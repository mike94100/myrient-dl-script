use anyhow::Result;
use reqwest::Client;
use scraper::{Html, Selector};
use tokio::sync::Semaphore;
use std::sync::Arc;

use crate::cache::CacheManager;
use crate::toml_utils::{discover_and_organize_platforms, get_url_file_path};
use crate::filters;

use html_escape::decode_html_entities;
use urlencoding::encode;

async fn scrape_html(client: &Client, cache: Option<&CacheManager>, url: &str) -> Result<String> {
    if let Some(c) = cache { if let Some(s) = c.get(url) { return Ok(s); } }
    let resp = client.get(url).send().await?;
    let text = resp.text().await?;
    if let Some(c) = cache { let _ = c.put(url, &text); }
    Ok(text)
}

fn scrape_zip_links(html: &str) -> Vec<(String, String)> {
    // Returns (href, title) pairs
    let doc = Html::parse_document(html);
    let sel = Selector::parse("a").unwrap();
    let mut links = Vec::new();
    for el in doc.select(&sel) {
        if let Some(href) = el.value().attr("href") {
            if href.ends_with(".zip") {
                let raw_title = el.value().attr("title").unwrap_or(href);
                let decoded_title = decode_html_entities(raw_title).to_string();
                links.push((href.to_string(), decoded_title));
            }
        }
    }
    // Sort by title (human-readable name)
    links.sort_by(|a, b| a.1.cmp(&b.1));
    links
}

async fn generate_platform_urls(collection_path: &str, platform: &str, cache: Option<&CacheManager>, client: &Client, skip_excluded: bool) -> bool {
    let content = std::fs::read_to_string(collection_path).unwrap_or_default();
    let parsed: toml::Value = match toml::from_str(&content) { Ok(v) => v, Err(_) => return false };
    let platform_cfg = parsed.get("roms").and_then(|t| t.get(platform)).or_else(|| parsed.get("bios").and_then(|t| t.get(platform)));
    if platform_cfg.is_none() { return false; }
    let cfg = platform_cfg.unwrap();
    let url = cfg.get("url").and_then(|v| v.as_str()).unwrap_or("");
    if url.is_empty() { return false; }

    let html = match scrape_html(client, cache, url).await { Ok(h) => h, Err(_) => return false };
    let links = scrape_zip_links(&html);
    // Apply collection filters (dedupe/include/exclude) using human-readable name
    let titles: Vec<String> = links.iter().map(|(_, title)| title.clone()).collect();
    let filtered_titles = match filters::filter_collection_apply(collection_path, platform, &titles) {
        Ok(v) => v,
        Err(_) => titles.clone(),
    };
    // Generate URLs, prepending excluded ones with #
    let urls = generate_urls(&links, &filtered_titles, url, skip_excluded);
    let path = get_url_file_path(collection_path, platform);
    if let Ok(mut f) = std::fs::File::create(&path) {
        use std::io::Write;
        let _ = f.write_all(urls.join("\n").as_bytes());
        let _ = f.write_all(b"\n");
    }
    true
}

pub async fn process_platforms(collection_path: &str, platforms: Vec<String>, cache: Option<CacheManager>, progress_callback: Option<Arc<dyn Fn(&str) + Send + Sync>>, skip_excluded: bool) -> usize {
    let client = Client::builder().user_agent("MyrientGen/1.0").build().unwrap();
    let max = std::cmp::min(8, platforms.len());
    let sem = Arc::new(Semaphore::new(max));
    let cache_ref = cache.as_ref();
    let mut handles = Vec::new();

    for p in platforms.clone() {
        let c = client.clone();
        let sem = sem.clone();
        let coll = collection_path.to_string();
        let cache_clone = cache_ref.cloned();
        let progress_callback = progress_callback.clone();

        let handle = tokio::spawn(async move {
            let _permit = sem.acquire_owned().await.unwrap();

            // Report progress: starting platform
            if let Some(ref cb) = progress_callback {
                cb(&format!("Processing platform: {}", p));
            }

            let result = generate_platform_urls(&coll, &p, cache_clone.as_ref(), &c, skip_excluded).await;

            // Report progress: completed platform
            if let Some(ref cb) = progress_callback {
                if result {
                    cb(&format!("✓ Generated URLs for {}", p));
                } else {
                    cb(&format!("✗ Failed to generate URLs for {}", p));
                }
            }

            result
        });
        handles.push(handle);
    }

    let mut success = 0usize;
    for h in handles { if let Ok(r) = h.await { if r { success += 1 } } }
    success
}

pub async fn generate_collection_urls(collection_path: &str, cache_manager: Option<CacheManager>, dry_run: bool, progress_callback: Option<Arc<dyn Fn(&str) + Send + Sync>>, skip_excluded: bool) -> bool {
    if let Some(ref cb) = progress_callback {
        cb("Discovering platforms...");
    }

    let (filter, nofilter) = match discover_and_organize_platforms(collection_path) { Ok(v) => v, Err(_) => {
        if let Some(ref cb) = progress_callback {
            cb("Failed to discover platforms");
        }
        eprintln!("Failed to discover platforms for {}", collection_path);
        return false
    } };

    let total = filter.len() + nofilter.len();
    if dry_run {
        if let Some(ref cb) = progress_callback {
            cb(&format!("DRY RUN: would generate for {} platforms", total));
        }
        println!("DRY RUN: would generate for {} platforms", total);
        return true
    }

    if filter.is_empty() && nofilter.is_empty() {
        if let Some(ref cb) = progress_callback {
            cb("No platforms to process - all URL files exist");
        }
        return true
    }

    if let Some(ref cb) = progress_callback {
        cb(&format!("Processing {} platforms...", filter.len()));
    }

    let success_count = process_platforms(collection_path, filter, cache_manager, progress_callback, skip_excluded).await;

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



fn generate_urls(links: &[(String, String)], filtered_titles: &[String], base_url: &str, skip_excluded: bool) -> Vec<String> {
    links.iter().filter_map(|(_href, title)| {
        // Encode title
        let encoded_filename = encode(title);
        let full = format!("{}/{}", base_url.trim_end_matches('/'), encoded_filename);
        // Write URL if allowed title
        if filtered_titles.contains(title) {
            Some(full)
        } else {
            // Skip excluded URLs if set
            if skip_excluded {
                None
            // Comment out excluded URLs by default
            } else {
                Some(format!("#{}", full))
            }
        }
    }).collect()
}
