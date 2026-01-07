use std::path::Path;
use std::time::Duration;

use anyhow::Result;
use reqwest::Client;
use scraper::{Html, Selector};
use tokio::sync::Semaphore;

use crate::backend::cache::CacheManager;
use crate::backend::toml_utils::{discover_and_organize_platforms, get_url_file_path};

pub async fn scrape_platform_html(client: &Client, cache: Option<&CacheManager>, url: &str) -> Result<String> {
    if let Some(cm) = cache {
        if let Some(cached) = cm.get(url) {
            return Ok(cached);
        }
    }

    let resp = client.get(url).timeout(Duration::from_secs(30)).send().await?;
    let text = resp.text().await?;

    if let Some(cm) = cache {
        let _ = cm.put(url, &text);
    }

    Ok(text)
}

fn scrape_zip_filenames(html: &str) -> Vec<String> {
    let document = Html::parse_document(html);
    let selector = Selector::parse("a").unwrap();
    let mut files = Vec::new();
    for element in document.select(&selector) {
        if let Some(href) = element.value().attr("href") {
            if href.ends_with(".zip") {
                let text = element.text().collect::<Vec<_>>().join("").trim().to_string();
                if !text.is_empty() {
                    files.push(text);
                }
            }
        }
    }
    files.sort();
    files
}

fn generate_urls_from_files(files: &[String], base_url: &str) -> Vec<String> {
    use url::percent_encoding::{utf8_percent_encode, NON_ALPHANUMERIC};
    let mut urls = Vec::new();
    for f in files {
        let clean = f.trim_start_matches('#');
        let enc = utf8_percent_encode(clean, NON_ALPHANUMERIC).to_string();
        let mut full = format!("{}/{}", base_url.trim_end_matches('/'), enc);
        if f.starts_with('#') {
            full = format!("#{}", full);
        }
        urls.push(full);
    }
    urls
}

async fn generate_platform_urls(collection_path: &str, platform: &str, cache: Option<&CacheManager>, client: &Client) -> bool {
    // Minimal implementation: read TOML, find platform URL under roms or bios
    let content = std::fs::read_to_string(collection_path);
    if content.is_err() {
        return false;
    }
    let parsed: toml::Value = match toml::from_str(&content.unwrap()) {
        Ok(v) => v,
        Err(_) => return false,
    };

    let platform_config = parsed.get("roms").and_then(|t| t.get(platform)).or_else(|| parsed.get("bios").and_then(|t| t.get(platform)));
    if platform_config.is_none() {
        return false;
    }
    let cfg = platform_config.unwrap();
    let url = cfg.get("url").and_then(|v| v.as_str()).unwrap_or("");
    if url.is_empty() { return false; }

    let html = match scrape_platform_html(client, cache, url).await {
        Ok(h) => h,
        Err(_) => return false,
    };

    let files = scrape_zip_filenames(&html);
    if files.is_empty() {
        return false;
    }

    // TODO: apply filters; for now use all files
    let urls = generate_urls_from_files(&files.iter().map(|s| s.to_string()).collect::<Vec<_>>(), url);

    let path = get_url_file_path(collection_path, platform);
    if let Ok(mut file) = std::fs::File::create(&path) {
        use std::io::Write;
        let _ = file.write_all(urls.join("\n").as_bytes());
        let _ = file.write_all(b"\n");
    }

    true
}

pub async fn process_platforms_async(collection_path: &str, platforms: Vec<String>, cache: Option<CacheManager>) -> usize {
    let client = Client::builder().user_agent("MyrientDL/1.0").build().unwrap();
    let max_concurrent = std::cmp::min(4, platforms.len());
    let semaphore = Semaphore::new(max_concurrent);

    let cache_ref = cache.as_ref();

    let mut handles = vec![];
    for platform in platforms {
        let client = client.clone();
        let sem = semaphore.clone();
        let coll = collection_path.to_string();
        let cache_clone = cache_ref.cloned();
        let handle = tokio::spawn(async move {
            let _permit = sem.acquire().await;
            generate_platform_urls(&coll, &platform, cache_clone.as_ref(), &client).await
        });
        handles.push(handle);
    }

    let mut success = 0usize;
    for h in handles {
        if let Ok(result) = h.await {
            if result { success += 1 }
        }
    }
    success
}

pub async fn generate_collection_urls_async(collection_path: &str, cache_manager: Option<CacheManager>, _dry_run: bool) -> bool {
    // Discover platforms
    let (filter_platforms, nofilter_platforms) = match discover_and_organize_platforms(collection_path) {
        Ok(v) => v,
        Err(_) => return false,
    };

    let total = filter_platforms.len() + nofilter_platforms.len();
    if total == 0 { return true; }

    let success_count = process_platforms_async(collection_path, filter_platforms, cache_manager).await;
    success_count == total
}

pub fn generate_readme_sync(_collection_path: &str, _dry_run: bool) -> bool {
    // Placeholder: README generation is not implemented yet
    true
}
