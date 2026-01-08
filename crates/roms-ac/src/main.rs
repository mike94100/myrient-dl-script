use std::path::{Path, PathBuf};
use std::sync::Arc;

use clap::Parser;
use anyhow::Result;
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};

mod cache;
mod toml_utils;
mod generator;
mod filters;
mod readme;
mod downloader;

use crate::cache::CacheManager;
use crate::generator::{generate_collection_urls};

use dirs;

#[derive(Parser)]
#[command(name = "roms-ac")]
#[command(about = "Generate URL files, README, and download from collection TOML files")]
struct Args {
    /// Generate URL files
    #[arg(long)]
    gen_url: bool,

    /// Generate README
    #[arg(long)]
    gen_readme: bool,

    /// Download files listed in URL files
    #[arg(long)]
    download: bool,

    /// Platforms to download (only used with --download)
    #[arg(long, short='p')]
    platform: Vec<String>,

    /// Output directory for downloads
    #[arg(long, short='o')]
    output: Option<PathBuf>,

    /// Dry run
    #[arg(long)]
    dry_run: bool,

    /// Skip writing excluded URLs to files (default: write with # prefix)
    #[arg(long)]
    skip_excluded: bool,

    /// Collection TOML files
    #[arg(required = true)]
    files: Vec<PathBuf>,
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    if !args.gen_url && !args.gen_readme && !args.download {
        eprintln!("Must specify at least one of --gen-url, --gen-readme, or --download");
        std::process::exit(2);
    }

    // Remove duplicates, preserve order
    let mut seen = std::collections::HashSet::new();
    let files: Vec<PathBuf> = args.files.into_iter().filter(|p| {
        let s = p.to_string_lossy().to_string();
        if seen.contains(&s) { false } else { seen.insert(s); true }
    }).collect();

    // Setup progress bars for operations
    let multi_progress = MultiProgress::new();

    // Setup cache manager
    let cache = CacheManager::new(Path::new(".cache"), 24);

    let mut all_ok = true;

    for f in files {
        let filename = f.file_name().unwrap_or_default().to_string_lossy();
        let filename_str = filename.to_string(); // Clone for use in multiple places
        println!("Processing {}", filename_str);

        if args.gen_url {
            // For dry runs, use simple output without progress bar
            if args.dry_run {
                println!("Checking URL generation for {}", filename_str);
                let ok = generate_collection_urls(f.to_str().unwrap(), Some(cache.clone()), args.dry_run, None, args.skip_excluded).await;
                if ok {
                    println!("✓ Dry run completed for {}", filename_str);
                } else {
                    all_ok = false;
                    println!("✗ Dry run failed for {}", filename_str);
                    eprintln!("URL generation failed for {}", f.display());
                }
            } else {
                // Track successful and failed platforms for summary
                let successful_platforms = std::sync::Arc::new(std::sync::Mutex::new(Vec::<String>::new()));
                let failed_platforms = std::sync::Arc::new(std::sync::Mutex::new(Vec::<String>::new()));
                let successful_clone = successful_platforms.clone();
                let failed_clone = failed_platforms.clone();

                // Create progress bar that shows platform completion
                let pb = multi_progress.add(ProgressBar::new(0));
                pb.set_style(
                    ProgressStyle::default_bar()
                        .template("{spinner:.cyan} [{bar:25}] {pos}/{len} [{elapsed_precise}] {msg}")?
                        .tick_chars("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
                );
                pb.enable_steady_tick(std::time::Duration::from_millis(60));
                pb.set_message("Discovering platforms...");

                // Clone filename for the closure
                let pb_clone = pb.clone();

                // Track currently processing platforms
                let processing_platforms = std::sync::Arc::new(std::sync::Mutex::new(std::collections::HashSet::new()));
                let processing_clone = processing_platforms.clone();

                // Track completion for progress bar
                let completed = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
                let total_platforms = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
                let completed_clone = completed.clone();
                let total_clone = total_platforms.clone();

                // Create progress callback that updates the progress bar
                let progress_callback: Arc<dyn Fn(&str) + Send + Sync> = Arc::new(move |msg: &str| {
                    if msg.starts_with("✓ Generated URLs for ") {
                        // Track successful platform
                        let platform = msg.trim_start_matches("✓ Generated URLs for ");
                        if let Ok(mut successful) = successful_clone.lock() {
                            successful.push(platform.to_string());
                        }
                        // Remove from processing
                        if let Ok(mut processing) = processing_clone.lock() {
                            processing.remove(platform);
                        }

                        // Update progress
                        let current = completed_clone.fetch_add(1, std::sync::atomic::Ordering::SeqCst) + 1;
                        pb_clone.set_position(current as u64);

                        // Update message with currently processing platforms
                        update_progress_message(&pb_clone, &processing_clone, current, &total_clone);

                    } else if msg.starts_with("✗ Failed to generate URLs for ") {
                        // Track failed platform
                        let platform = msg.trim_start_matches("✗ Failed to generate URLs for ");
                        if let Ok(mut failed) = failed_clone.lock() {
                            failed.push(platform.to_string());
                        }
                        // Remove from processing
                        if let Ok(mut processing) = processing_clone.lock() {
                            processing.remove(platform);
                        }

                        // Still count as completed for progress bar
                        let current = completed_clone.fetch_add(1, std::sync::atomic::Ordering::SeqCst) + 1;
                        pb_clone.set_position(current as u64);

                        // Update message with currently processing platforms
                        update_progress_message(&pb_clone, &processing_clone, current, &total_clone);

                    } else if msg.starts_with("Processing platform: ") {
                        // Add to processing list
                        let platform = msg.trim_start_matches("Processing platform: ");
                        if let Ok(mut processing) = processing_clone.lock() {
                            processing.insert(platform.to_string());
                        }

                        // Update message with currently processing platforms
                        let current = completed_clone.load(std::sync::atomic::Ordering::SeqCst);
                        update_progress_message(&pb_clone, &processing_clone, current, &total_clone);

                    } else if msg.starts_with("Processing ") && msg.contains(" platforms...") {
                        // Extract total count and set progress bar length
                        if let Some(count_str) = msg.split("Processing ").nth(1).and_then(|s| s.split(" platforms").next()) {
                            if let Ok(count) = count_str.parse::<usize>() {
                                total_clone.store(count, std::sync::atomic::Ordering::SeqCst);
                                pb_clone.set_length(count as u64);
                                pb_clone.set_message("Processing platforms...");
                            }
                        }
                    } else {
                        // Keep current message for other status updates
                        pb_clone.set_message(msg.to_string());
                    }
                });

                // Helper function to update progress bar message
                fn update_progress_message(
                    pb: &ProgressBar,
                    processing: &std::sync::Arc<std::sync::Mutex<std::collections::HashSet<String>>>,
                    current: usize,
                    total: &std::sync::Arc<std::sync::atomic::AtomicUsize>,
                ) {
                    let total_num = total.load(std::sync::atomic::Ordering::SeqCst);
                    if let Ok(processing_lock) = processing.lock() {
                        let processing_count = processing_lock.len();
                        if processing_count == 0 {
                            pb.set_message(format!("{}/{} completed", current, total_num));
                        } else {
                            pb.set_message(format!("Processing {} platform(s)", processing_count));
                        }
                    }
                }

                // Modify the function call to accept the progress callback
                let ok = generate_collection_urls(f.to_str().unwrap(), Some(cache.clone()), args.dry_run, Some(progress_callback), args.skip_excluded).await;

                // Print detailed summary after progress bar completes
                if let Ok(mut successful) = successful_platforms.lock() {
                    if !successful.is_empty() {
                        successful.sort();
                        println!("✓ Successfully generated URLs for platforms: {}", successful.join(", "));
                    }
                }
                if let Ok(mut failed) = failed_platforms.lock() {
                    if !failed.is_empty() {
                        failed.sort();
                        println!("✗ Failed to generate URLs for platforms: {}", failed.join(", "));
                    }
                }

                // Don't show finish message to avoid repeating progress bar
                if !ok {
                    all_ok = false;
                    eprintln!("URL generation failed for {}", f.display());
                }
            }
        }

        if args.gen_readme {
            // Discover total platforms first for accurate progress bar
            let total_platforms = match toml_utils::discover_and_organize_platforms(f.to_str().unwrap()) {
                Ok((filter, nofilter)) => filter.len() + nofilter.len(),
                Err(_) => 0,
            };

            // Create progress bar for README generation (per-platform progress)
            let pb = multi_progress.add(ProgressBar::new(0));
            pb.set_style(
                ProgressStyle::default_bar()
                    .template("{spinner:.cyan} [{bar:25}] {pos}/{len} [{elapsed_precise}] {msg}")?
                    .tick_chars("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
            );
            pb.enable_steady_tick(std::time::Duration::from_millis(60));
            pb.set_length(total_platforms as u64);
            pb.set_message("Starting README generation...");

            // Track platforms processed for README
            let processed_count = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
            let processed_clone = processed_count.clone();

            // Create progress callback for README generation
            let pb_clone = pb.clone();
            let readme_progress: Arc<dyn Fn(&str) + Send + Sync> = Arc::new(move |msg: &str| {
                if msg.starts_with("Fetching sizes for ") && msg.ends_with(" platform...") {
                    // Update progress for each platform
                    let current = processed_clone.fetch_add(1, std::sync::atomic::Ordering::SeqCst) + 1;
                    pb_clone.set_position(current as u64);
                    pb_clone.set_message(format!("Processing platforms ({}/{})", current, total_platforms));
                } else if msg.starts_with("✓ Fetched sizes for ") {
                    // Platform completed
                    pb_clone.set_message("Building README content...");
                }
            });

            // README generation may perform blocking network I/O; run it in a blocking task
            let fp = f.clone();
            let filename_clone = filename_str.clone();
            match tokio::task::spawn_blocking(move || {
                readme::generate_readme(fp.to_str().unwrap(), Some(&*readme_progress))
            }).await {
                Ok(Ok(v)) => {
                    if v {
                        pb.finish_with_message(format!("✓ README generated for {}", filename_clone));
                    } else {
                        all_ok = false;
                        pb.finish_with_message(format!("✗ README generation failed for {}", filename_clone));
                        eprintln!("README generation failed for {}", f.display());
                    }
                }
                Ok(Err(e)) => {
                    all_ok = false;
                    pb.finish_with_message(format!("✗ README error for {}", filename_clone));
                    eprintln!("README generation error for {}: {}", f.display(), e);
                }
                Err(e) => {
                    all_ok = false;
                    pb.finish_with_message(format!("✗ README panicked for {}", filename_clone));
                    eprintln!("README generation panicked for {}: {}", f.display(), e);
                }
            }
        }

        if args.download {
            let pb = multi_progress.add(ProgressBar::new_spinner());
            pb.set_style(
                ProgressStyle::default_spinner()
                    .template("{spinner} Downloading for {msg}...")?
            );
            pb.set_message(filename.to_string());

            let out = args.output.clone().unwrap_or_else(|| {
                dirs::home_dir()
                    .unwrap_or_else(|| PathBuf::from("."))
                    .join("Downloads")
            });
            // determine platforms: use provided list or all platforms from TOML
            let platforms = if !args.platform.is_empty() {
                args.platform.clone()
            } else {
                // discover platforms
                match toml::from_str::<toml::Value>(&std::fs::read_to_string(&f).unwrap_or_default()) {
                    Ok(val) => {
                        let mut ps = Vec::new();
                        if let Some(r) = val.get("roms").and_then(|v| v.as_table()) { for k in r.keys() { ps.push(k.clone()); } }
                        if let Some(b) = val.get("bios").and_then(|v| v.as_table()) { for k in b.keys() { ps.push(k.clone()); } }
                        ps
                    }
                    Err(_) => vec![],
                }
            };

            let ok = downloader::download_collection_async(f.to_str().unwrap(), platforms, out.to_str().unwrap()).await?;
            if ok {
                pb.finish_with_message(format!("✓ Download complete for {}", filename));
            } else {
                all_ok = false;
                pb.finish_with_message(format!("✗ Download failed for {}", filename));
                eprintln!("Download failed for {}", f.display());
            }
        }
    }

    if all_ok {
        println!("✓ Completed successfully");
        Ok(())
    } else {
        println!("✗ Some operations failed");
        std::process::exit(1)
    }
}
