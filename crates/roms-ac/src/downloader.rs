use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::collections::BTreeMap;

use clap::Parser;
use anyhow::Result;
use tokio::fs::File;
use tokio::io::AsyncWriteExt;
use tokio::sync::Semaphore;
use reqwest::Client;
use indicatif::{ProgressBar, ProgressStyle, MultiProgress};
use futures::stream::{self, StreamExt};
use percent_encoding::percent_decode_str;

#[derive(Parser)]
#[command(name = "myrient-dl")]
#[command(about = "Download ROM collections from Myrient")]
#[command(version = "1.0")]
struct Args {
    /// Collection TOML URL or local path
    #[arg(required = true)]
    collection: String,

    /// Output directory
    #[arg(short, long, default_value = "downloads")]
    output: PathBuf,

    /// Platforms to download (if not specified, downloads all)
    #[arg(short = 'p', long)]
    platforms: Vec<String>,

    /// Dry run - show what would be downloaded
    #[arg(long)]
    dry_run: bool,

    /// Force overwrite existing files
    #[arg(long)]
    force: bool,

    /// Maximum concurrent downloads
    #[arg(long, default_value = "5")]
    max_concurrent: usize,

    /// Show individual file progress
    #[arg(long)]
    progress: bool,
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    println!("Myrient ROM Downloader");
    println!("Collection: {}", args.collection);
    println!("Output: {}", args.output.display());
    println!("Concurrent downloads: {}", args.max_concurrent);
    println!();

    // Create output directory
    if !args.dry_run {
        tokio::fs::create_dir_all(&args.output).await?;
    }

    // Load collection TOML
    let collection_content = if args.collection.starts_with("http") {
        println!("Downloading collection configuration...");
        let client = Client::new();
        let response = client.get(&args.collection).send().await?;
        response.text().await?
    } else {
        tokio::fs::read_to_string(&args.collection).await?
    };

    let parsed: toml::Value = toml::from_str(&collection_content)?;

    // Extract platforms
    let mut roms = BTreeMap::new();
    if let Some(t) = parsed.get("roms").and_then(|v| v.as_table()) {
        for (k, v) in t {
            roms.insert(k.clone(), v.clone());
        }
    }

    // Filter platforms if specified
    let platforms_to_download: Vec<String> = if args.platforms.is_empty() {
        roms.keys().cloned().collect()
    } else {
        args.platforms.clone()
    };

    println!("Platforms to download: {}", platforms_to_download.join(", "));
    println!();

    let multi_progress = Arc::new(MultiProgress::new());
    let semaphore = Arc::new(Semaphore::new(args.max_concurrent));
    let client = Arc::new(Client::new());

    let mut total_files = 0;
    let mut download_tasks = Vec::new();

    for platform in platforms_to_download {
        if let Some(platform_config) = roms.get(&platform) {
            println!("Processing platform: {}", platform);

            // Get URL file path - check if it's specified in the platform config
            let url_file_path = platform_config.get("urllist")
                .and_then(|v| v.as_str())
                .unwrap_or(&format!("urls/{}/{}.txt", platform, platform));

            // Construct full URL for URL file
            let url_file_url = if args.collection.starts_with("http") && url_file_path.starts_with("urls/") {
                // If collection is remote and URL file path is relative, construct full URL
                let base_url = args.collection.trim_end_matches("/").rsplitn(2, '/').nth(1)
                    .map(|s| format!("https://raw.githubusercontent.com/mike94100/roms-as-code/main/{}", s))
                    .unwrap_or_else(|| "https://raw.githubusercontent.com/mike94100/roms-as-code/main".to_string());
                format!("{}/{}", base_url, url_file_path)
            } else if url_file_path.starts_with("http") {
                // URL file is already a full URL
                url_file_path.to_string()
            } else {
                // Local file
                url_file_path.to_string()
            };

            // Load URL file
            let url_content = if url_file_url.starts_with("http") {
                let response = client.get(&url_file_url).send().await?;
                response.text().await?
            } else {
                tokio::fs::read_to_string(&url_file_path).await?
            };

            let urls: Vec<String> = url_content
                .lines()
                .map(|line| line.trim())
                .filter(|line| !line.is_empty() && !line.starts_with('#'))
                .map(|line| line.to_string())
                .collect();

            println!("  Found {} URLs", urls.len());

            let platform_output = args.output.join("roms").join(&platform);
            if !args.dry_run {
                tokio::fs::create_dir_all(&platform_output).await?;
            }

            for url in urls {
                if let Some(filename) = url.rsplit('/').next() {
                    let decoded_filename = percent_decode_str(filename).decode_utf8_lossy();
                    let output_path = platform_output.join(decoded_filename.as_ref());

                    total_files += 1;

                    if args.dry_run {
                        println!("  Would download: {}", decoded_filename);
                    } else {
                        let task = download_file(
                            client.clone(),
                            semaphore.clone(),
                            multi_progress.clone(),
                            url,
                            output_path,
                            args.force,
                            args.progress,
                        );
                        download_tasks.push(task);
                    }
                }
            }

            println!("  Queued platform: {}", platform);
            println!();
        } else {
            eprintln!("Warning: Platform '{}' not found in collection", platform);
        }
    }

    if !args.dry_run {
        println!("Starting downloads...");
        let results = stream::iter(download_tasks)
            .buffer_unordered(args.max_concurrent)
            .collect::<Vec<_>>()
            .await;

        let successful = results.iter().filter(|r| r.is_ok()).count();
        println!("\nDownload complete!");
        println!("Total files processed: {}", total_files);
        println!("Files downloaded successfully: {}", successful);
        println!("Failed downloads: {}", total_files - successful);
    } else {
        println!("Dry run complete!");
        println!("Total files that would be processed: {}", total_files);
    }

    Ok(())
}

async fn download_file(
    client: Arc<Client>,
    semaphore: Arc<Semaphore>,
    multi_progress: Arc<MultiProgress>,
    url: String,
    output_path: PathBuf,
    force: bool,
    show_progress: bool,
) -> Result<()> {
    let _permit = semaphore.acquire().await?;

    // Check if file exists
    if output_path.exists() && !force {
        return Ok(());
    }

    let filename = output_path.file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown");

    // Create progress bar
    let pb = if show_progress {
        let pb = multi_progress.add(ProgressBar::new(0));
        pb.set_style(
            ProgressStyle::default_bar()
                .template("{msg} [{bar:40.cyan/blue}] {bytes}/{total_bytes} ({eta})")?
                .progress_chars("#>-")
        );
        pb.set_message(filename.to_string());
        Some(pb)
    } else {
        None
    };

    // Download file
    let response = client.get(&url).send().await?;
    let total_size = response.content_length().unwrap_or(0);

    if let Some(pb) = &pb {
        pb.set_length(total_size);
    }

    let mut file = File::create(&output_path).await?;
    let mut stream = response.bytes_stream();

    while let Some(chunk) = stream.next().await {
        let chunk = chunk?;
        file.write_all(&chunk).await?;

        if let Some(pb) = &pb {
            pb.inc(chunk.len() as u64);
        }
    }

    if let Some(pb) = pb {
        pb.finish_with_message(format!("✓ {}", filename));
    }

    Ok(())
}