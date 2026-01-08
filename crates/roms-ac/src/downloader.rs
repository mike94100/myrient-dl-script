use std::path::Path;
use anyhow::Result;
use reqwest::Client;
use percent_encoding::percent_decode_str;
use indicatif::{ProgressBar, ProgressStyle, MultiProgress};
use futures::stream::{self, StreamExt};

#[derive(Clone)]
struct DownloadTask {
    url: String,
    filename: String,
    output_path: std::path::PathBuf,
}

pub async fn download_collection_async(collection_path: &str, platforms: Vec<String>, output_dir: &str) -> Result<bool> {
    let client = Client::builder().user_agent("MyrientGen/1.0").build().unwrap();

    // Collect all download tasks from all platforms
    let mut download_tasks = Vec::new();

    for platform in platforms.iter() {
        let url_file = crate::toml_utils::get_url_file_path(collection_path, platform);
        if !url_file.exists() {
            eprintln!("URL file not found for {}: {}", platform, url_file.display());
            return Ok(false);
        }
        let content = match std::fs::read_to_string(&url_file) {
            Ok(s) => s,
            Err(e) => {
                eprintln!("Failed to read {}: {}", url_file.display(), e);
                return Ok(false);
            }
        };

        // Get the directory from the collection config
        let directory = if let Ok(dir) = crate::toml_utils::get_toml_value::<String>(collection_path, &format!("roms.{}.directory", platform)) {
            dir
        } else if let Ok(dir) = crate::toml_utils::get_toml_value::<String>(collection_path, &format!("bios.{}.directory", platform)) {
            dir
        } else {
            platform.to_string() // fallback to platform name
        };

        let out_dir = Path::new(output_dir).join(directory);
        let _ = std::fs::create_dir_all(&out_dir);

        for line in content.lines() {
            let url = line.trim();
            if url.is_empty() || url.starts_with('#') {
                continue;
            }

            // Determine filename from URL
            let filename = if let Some(seg) = url.rsplit('/').next() {
                percent_decode_str(seg).decode_utf8_lossy().to_string()
            } else {
                continue;
            };

            let output_path = out_dir.join(&filename);

            download_tasks.push(DownloadTask {
                url: url.to_string(),
                filename,
                output_path,
            });
        }
    }

    // Create a shared progress bar area
    let multi_progress = std::sync::Arc::new(MultiProgress::new());

    // Create a vector to hold active progress bars (up to 5)
    let active_bars = std::sync::Arc::new(std::sync::Mutex::new(Vec::<ProgressBar>::new()));
    let bars_clone = active_bars.clone();

    // Clone client for use in async tasks
    let client_clone = client.clone();

    // Process downloads concurrently with limit of 5
    let results = stream::iter(download_tasks)
        .map(|task| {
            let client = client_clone.clone();
            let multi_progress = multi_progress.clone();
            let bars_clone = bars_clone.clone();

            async move {
                // Get or create a progress bar
                let pb = {
                    let mut bars = bars_clone.lock().unwrap();
                    if bars.len() < 5 {
                        // Create new progress bar
                        let pb = multi_progress.add(ProgressBar::new(0));
                        pb.set_style(
                            ProgressStyle::default_bar()
                                .template("{msg} [{bar:30.cyan/blue}] {bytes}/{total_bytes} ({eta})")
                                .unwrap()
                                .progress_chars("#>-")
                        );
                        bars.push(pb.clone());
                        pb
                    } else {
                        // Reuse the first (oldest) progress bar
                        bars[0].clone()
                    }
                };

                // Truncate long filename or pad short filename for consistent positioning
                let display_name = if task.filename.len() > 30 {
                    format!("{:.27}...", task.filename)  // 27 chars + "..." = 30 chars
                } else {
                    format!("{:30}", task.filename)       // pad to 30 chars
                };
                pb.reset();
                pb.set_message(format!("{}", display_name));

                // Download file
                match client.get(&task.url).send().await {
                    Ok(mut resp) => {
                        if resp.status().is_success() {
                            let total_size = resp.content_length().unwrap_or(0);
                            pb.set_length(total_size);

                            match std::fs::File::create(&task.output_path) {
                                Ok(mut file) => {
                                    use std::io::Write;

                                    // Stream download in chunks
                                    let mut success = true;
                                    while let Ok(Some(chunk)) = resp.chunk().await {
                                        if let Err(e) = file.write_all(&chunk) {
                                            eprintln!("Failed to write to {}: {}", task.output_path.display(), e);
                                            pb.finish_with_message(format!("✗ {}", display_name));
                                            success = false;
                                            break;
                                        }
                                        pb.inc(chunk.len() as u64);
                                    }

                                    if success {
                                        pb.finish_with_message(format!("✓ {}", display_name));
                                        Ok(())
                                    } else {
                                        Err(anyhow::anyhow!("Write error for {}", task.filename))
                                    }
                                }
                                Err(e) => {
                                    eprintln!("Failed to create file: {}", task.output_path.display());
                                    pb.finish_with_message(format!("✗ {}", display_name));
                                    Err(anyhow::anyhow!("Create error: {}", e))
                                }
                            }
                        } else {
                            eprintln!("Failed to download {}: HTTP {}", task.url, resp.status());
                            pb.finish_with_message(format!("✗ {}", display_name));
                            Err(anyhow::anyhow!("HTTP error {} for {}", resp.status(), task.filename))
                        }
                    }
                    Err(e) => {
                        eprintln!("Request error for {}: {}", task.url, e);
                        pb.finish_with_message(format!("✗ {}", display_name));
                        Err(anyhow::anyhow!("Network error for {}: {}", task.filename, e))
                    }
                }
            }
        })
        .buffer_unordered(5)
        .collect::<Vec<_>>()
        .await;

    // Check if all downloads succeeded
    let failed_count = results.iter().filter(|r| r.is_err()).count();
    if failed_count > 0 {
        eprintln!("{} downloads failed", failed_count);
        Ok(false)
    } else {
        Ok(true)
    }
}
