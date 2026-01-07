use std::path::{Path, PathBuf};
use std::fs;
use std::io::Write;

use clap::Parser;
use anyhow::Result;
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};

mod cache;
mod toml_utils;
mod generator;
mod filters;
mod readme;

use crate::cache::CacheManager;
use crate::generator::{generate_collection_urls_async, generate_readme_sync};

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

    // Setup progress bars
    let multi_progress = MultiProgress::new();
    let overall_pb = multi_progress.add(ProgressBar::new(files.len() as u64));
    overall_pb.set_style(
        ProgressStyle::default_bar()
            .template("Overall: [{bar:40.cyan/blue}] {pos}/{len} files ({eta})")?
            .progress_chars("#>-")
    );
    overall_pb.set_message("Processing collections");

    // Setup cache manager
    let cache = CacheManager::new(Path::new(".cache"), 24);

    let mut all_ok = true;

    for f in files {
        let filename = f.file_name().unwrap_or_default().to_string_lossy();

        // Create per-file progress bar
        let file_pb = multi_progress.add(ProgressBar::new(1));
        file_pb.set_style(
            ProgressStyle::default_bar()
                .template(&format!("{}: [{{bar:30}}] {{msg}}", filename))?
                .progress_chars("#>-")
        );

        if args.gen_url {
            file_pb.set_message("Generating URLs...");
            let ok = generate_collection_urls_async(f.to_str().unwrap(), Some(cache.clone()), args.dry_run).await;
            if ok {
                file_pb.set_message("✓ URLs generated");
                file_pb.finish_with_message("✓ URLs generated");
            } else {
                all_ok = false;
                file_pb.set_message("✗ URL generation failed");
                file_pb.finish_with_message("✗ URL generation failed");
                eprintln!("URL generation failed for {}", f.display());
            }
        }

        if args.gen_readme {
            file_pb.set_message("Generating README...");
            // README generation may perform blocking network I/O; run it in a blocking task
            let fp = f.clone();
            match tokio::task::spawn_blocking(move || readme::generate_readme(fp.to_str().unwrap())).await {
                Ok(Ok(v)) => {
                    if v {
                        file_pb.set_message("✓ README generated");
                        file_pb.finish_with_message("✓ README generated");
                    } else {
                        all_ok = false;
                        file_pb.set_message("✗ README generation failed");
                        file_pb.finish_with_message("✗ README generation failed");
                        eprintln!("README generation failed for {}", f.display());
                    }
                }
                Ok(Err(e)) => {
                    all_ok = false;
                    file_pb.set_message("✗ README error");
                    file_pb.finish_with_message("✗ README error");
                    eprintln!("README generation error for {}: {}", f.display(), e);
                }
                Err(e) => {
                    all_ok = false;
                    file_pb.set_message("✗ README panicked");
                    file_pb.finish_with_message("✗ README panicked");
                    eprintln!("README generation panicked for {}: {}", f.display(), e);
                }
            }
        }

        if args.download {
            file_pb.set_message("Downloading...");
            let out = args.output.clone().unwrap_or_else(|| PathBuf::from("downloads"));
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

            let ok = generator::download_collection_async(f.to_str().unwrap(), platforms, out.to_str().unwrap()).await;
            if ok {
                file_pb.set_message("✓ Download complete");
                file_pb.finish_with_message("✓ Download complete");
            } else {
                all_ok = false;
                file_pb.set_message("✗ Download failed");
                file_pb.finish_with_message("✗ Download failed");
                eprintln!("Download failed for {}", f.display());
            }
        }

        overall_pb.inc(1);
    }

    overall_pb.finish_with_message("All collections processed");

    if all_ok {
        println!("✓ Completed successfully");
        Ok(())
    } else {
        println!("✗ Some operations failed");
        std::process::exit(1)
    }
}
