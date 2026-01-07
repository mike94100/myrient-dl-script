use std::path::Path;
use anyhow::Result;
use reqwest::Client;
use scraper::{Html, Selector};
use tokio::sync::Semaphore;
use std::sync::Arc;

use crate::cache::CacheManager;
use crate::toml_utils::{discover_and_organize_platforms, get_url_file_path};
use crate::filters;

async fn scrape_html(client: &Client, cache: Option<&CacheManager>, url: &str) -> Result<String> {
    if let Some(c) = cache { if let Some(s) = c.get(url) { return Ok(s); } }
    let resp = client.get(url).send().await?;
    let text = resp.text().await?;
    if let Some(c) = cache { let _ = c.put(url, &text); }
    Ok(text)
}

fn scrape_zip_filenames(html: &str) -> Vec<String> {
    let doc = Html::parse_document(html);
    let sel = Selector::parse("a").unwrap();
    let mut files = Vec::new();
    for el in doc.select(&sel) {
        if let Some(href) = el.value().attr("href") {
            if href.ends_with(".zip") {
                let text = el.text().collect::<Vec<_>>().join("").trim().to_string();
                if !text.is_empty() { files.push(text); }
            }
        }
    }
    files.sort();
    files
}

fn generate_urls_from_files(files: &[String], base_url: &str) -> Vec<String> {
    use percent_encoding::{utf8_percent_encode, NON_ALPHANUMERIC};
    let mut urls = Vec::new();
    for f in files {
        let clean = f.trim_start_matches('#');
        let enc = utf8_percent_encode(clean, NON_ALPHANUMERIC).to_string();
        let mut full = format!("{}/{}", base_url.trim_end_matches('/'), enc);
        if f.starts_with('#') { full = format!("#{}", full); }
        urls.push(full);
    }
    urls
}

async fn generate_platform_urls(collection_path: &str, platform: &str, cache: Option<&CacheManager>, client: &Client) -> bool {
    let content = std::fs::read_to_string(collection_path).unwrap_or_default();
    let parsed: toml::Value = match toml::from_str(&content) { Ok(v) => v, Err(_) => return false };
    let platform_cfg = parsed.get("roms").and_then(|t| t.get(platform)).or_else(|| parsed.get("bios").and_then(|t| t.get(platform)));
    if platform_cfg.is_none() { return false; }
    let cfg = platform_cfg.unwrap();
    let url = cfg.get("url").and_then(|v| v.as_str()).unwrap_or("");
    if url.is_empty() { return false; }

    let html = match scrape_html(client, cache, url).await { Ok(h) => h, Err(_) => return false };
    let files = scrape_zip_filenames(&html);
    // Apply collection filters (dedupe/include/exclude) if present
    let filtered_files = match filters::filter_collection_apply(collection_path, platform, &files) {
        Ok(v) => v,
        Err(_) => files.clone(),
    };
    if files.is_empty() { return false; }
    let urls = generate_urls_from_files(&filtered_files, url);
    let path = get_url_file_path(collection_path, platform);
    if let Ok(mut f) = std::fs::File::create(&path) {
        use std::io::Write;
        let _ = f.write_all(urls.join("\n").as_bytes());
        let _ = f.write_all(b"\n");
    }
    true
}

pub async fn process_platforms_async(collection_path: &str, platforms: Vec<String>, cache: Option<CacheManager>) -> usize {
    let client = Client::builder().user_agent("MyrientGen/1.0").build().unwrap();
    let max = std::cmp::min(4, platforms.len());
    let sem = Arc::new(Semaphore::new(max));
    let cache_ref = cache.as_ref();
    let mut handles = Vec::new();
    for p in platforms {
        let c = client.clone();
        let sem = sem.clone();
        let coll = collection_path.to_string();
        let cache_clone = cache_ref.cloned();
        let handle = tokio::spawn(async move {
            let _permit = sem.acquire_owned().await.unwrap();
            generate_platform_urls(&coll, &p, cache_clone.as_ref(), &c).await
        });
        handles.push(handle);
    }
    let mut success = 0usize;
    for h in handles { if let Ok(r) = h.await { if r { success += 1 } } }
    success
}

pub async fn generate_collection_urls_async(collection_path: &str, cache_manager: Option<CacheManager>, dry_run: bool) -> bool {
    let (filter, nofilter) = match discover_and_organize_platforms(collection_path) { Ok(v) => v, Err(_) => { eprintln!("Failed to discover platforms for {}", collection_path); return false } };
    println!("Discovered filter platforms: {:?}", filter);
    println!("Discovered nofilter platforms: {:?}", nofilter);
    let total = filter.len() + nofilter.len();
    if dry_run { println!("DRY RUN: would generate for {} platforms", total); return true }
    if filter.is_empty() && nofilter.is_empty() { return true }
    let success_count = process_platforms_async(collection_path, filter, cache_manager).await;

    // Count existing URL files for nofilter platforms as successful
    let mut successful_platforms = success_count;
    for platform_name in nofilter.iter() {
        let url_file = get_url_file_path(collection_path, platform_name);
        if url_file.exists() {
            successful_platforms += 1;
        } else {
            eprintln!("Warning: no URL file found for nofilter platform {}", platform_name);
        }
    }

    successful_platforms == total
}

pub async fn download_collection_async(collection_path: &str, platforms: Vec<String>, output_dir: &str) -> bool {
    let client = Client::builder().user_agent("MyrientGen/1.0").build().unwrap();

    for platform in platforms.iter() {
        let url_file = get_url_file_path(collection_path, platform);
        if !url_file.exists() {
            eprintln!("URL file not found for {}: {}", platform, url_file.display());
            return false;
        }
        let content = match std::fs::read_to_string(&url_file) { Ok(s) => s, Err(e) => { eprintln!("Failed to read {}: {}", url_file.display(), e); return false; } };

        let out_dir = Path::new(output_dir).join(platform);
        let _ = std::fs::create_dir_all(&out_dir);

        for line in content.lines() {
            let url = line.trim();
            if url.is_empty() || url.starts_with('#') { continue; }
            // Download file
            match client.get(url).send().await {
                Ok(resp) => {
                    if resp.status().is_success() {
                        if let Ok(bytes) = resp.bytes().await {
                            // Determine filename from URL
                            if let Some(seg) = url.rsplit('/').next() {
                                let filename = percent_encoding::percent_decode_str(seg).decode_utf8_lossy();
                                let path = out_dir.join(filename.to_string());
                                if let Ok(mut f) = std::fs::File::create(&path) {
                                    use std::io::Write;
                                    let _ = f.write_all(&bytes);
                                }
                            }
                        }
                    } else {
                        eprintln!("Failed to download {}: HTTP {}", url, resp.status());
                    }
                }
                Err(e) => {
                    eprintln!("Request error for {}: {}", url, e);
                }
            }
        }
    }

    true
}

pub fn generate_readme_sync(collection_path: &str, _dry_run: bool) -> bool {
    // Simple README: list platforms and counts from url files
    let content = std::fs::read_to_string(collection_path).unwrap_or_default();
    let parsed: toml::Value = match toml::from_str(&content) { Ok(v) => v, Err(_) => return false };
    let mut platforms = Vec::new();
    if let Some(roms) = parsed.get("roms").and_then(|v| v.as_table()) { platforms.extend(roms.keys().cloned()); }
    if let Some(bios) = parsed.get("bios").and_then(|v| v.as_table()) { platforms.extend(bios.keys().cloned()); }

    let mut out = String::new();
    out.push_str(&format!("# {}\n\n", Path::new(collection_path).file_name().unwrap().to_string_lossy()));
    for p in platforms {
        let path = get_url_file_path(collection_path, &p);
        if path.exists() {
            if let Ok(s) = std::fs::read_to_string(&path) {
                let count = s.lines().filter(|l| !l.trim().is_empty()).count();
                out.push_str(&format!("- {}: {} files\n", p, count));
            }
        } else {
            out.push_str(&format!("- {}: (no url file)\n", p));
        }
    }
    let readme_path = Path::new(collection_path).with_extension("README.md");
    let _ = std::fs::write(readme_path, out);
    true
}
