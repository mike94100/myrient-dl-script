use std::path::{Path, PathBuf};
use std::fs;
use std::io::Write;

use clap::Parser;
use anyhow::Result;

mod cache;
mod toml_utils;
mod generator;
mod filters;
mod readme;

use crate::cache::CacheManager;
use crate::generator::{generate_collection_urls_async, generate_readme_sync};

#[derive(Parser)]
#[command(name = "myrient-gen")]
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

    if !args.gen_url && !args.gen_readme {
        eprintln!("Must specify at least one of --gen-url or --gen-readme");
        std::process::exit(2);
    }

    // Remove duplicates, preserve order
    let mut seen = std::collections::HashSet::new();
    let files: Vec<PathBuf> = args.files.into_iter().filter(|p| {
        let s = p.to_string_lossy().to_string();
        if seen.contains(&s) { false } else { seen.insert(s); true }
    }).collect();

    // Setup cache manager
    let cache = CacheManager::new(Path::new(".cache"), 24);

    let mut all_ok = true;

    for f in files {
        println!("Processing {}", f.display());

        if args.gen_url {
            let ok = generate_collection_urls_async(f.to_str().unwrap(), Some(cache.clone()), args.dry_run).await;
            if !ok { all_ok = false; eprintln!("URL generation failed for {}", f.display()); }
        }

        if args.gen_readme {
            let ok = readme::generate_readme(f.to_str().unwrap());
            if !ok { all_ok = false; eprintln!("README generation failed for {}", f.display()); }
        }

        if args.download {
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
            if !ok { all_ok = false; eprintln!("Download failed for {}", f.display()); }
        }
    }

    if all_ok {
        println!("Completed successfully");
        Ok(())
    } else {
        std::process::exit(1)
    }
}
