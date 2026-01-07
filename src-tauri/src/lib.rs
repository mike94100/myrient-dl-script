use std::fs;
use serde::{Deserialize, Serialize};
mod backend;
use crate::backend::{CacheManager, generate_collection_urls_async, generate_readme_sync};

// Define structures for the frontend
#[derive(Serialize, Deserialize)]
struct PlatformInfo {
    name: String,
    r#type: String,
}

// Tauri commands

#[tauri::command]
async fn get_collections() -> Result<Vec<String>, String> {
    // Get list of collections from the collections directory
    // Use absolute path from the app directory
    let app_dir = std::env::current_dir().map_err(|e| format!("Failed to get current dir: {}", e))?;
    let collections_dir = app_dir.join("collections");

    println!("Looking for collections in: {:?}", collections_dir);

    if !collections_dir.exists() {
        println!("Collections directory doesn't exist: {:?}", collections_dir);
        return Ok(vec![]);
    }

    let mut collections = vec![];
    if let Ok(entries) = fs::read_dir(&collections_dir) {
        for entry in entries.flatten() {
            if let Some(file_name) = entry.file_name().to_str() {
                if file_name.ends_with(".toml") {
                    // Remove .toml extension
                    let collection_name = file_name.trim_end_matches(".toml");
                    println!("Found collection: {}", collection_name);
                    collections.push(collection_name.to_string());
                }
            }
        }
    }

    println!("Returning {} collections", collections.len());
    Ok(collections)
}

#[tauri::command]
async fn get_platforms(collection: String) -> Result<Vec<PlatformInfo>, String> {
    // Read TOML file and parse platforms
    let app_dir = std::env::current_dir().map_err(|e| format!("Failed to get current dir: {}", e))?;
    let toml_path = app_dir.join(format!("collections/{}.toml", collection));

    println!("Reading collection file: {:?}", toml_path);

    let content = fs::read_to_string(&toml_path)
        .map_err(|e| format!("Failed to read collection file: {}", e))?;

    // Parse TOML (simplified - in real app you'd use a proper TOML parser)
    let mut platforms = vec![];

    // Basic TOML parsing for ROMs and BIOS sections
    let roms_section = extract_section(&content, "roms");
    let bios_section = extract_section(&content, "bios");

    // Parse ROM platforms
    for line in roms_section.lines() {
        let line = line.trim();
        if line.starts_with('"') && line.contains("] =") {
            if let Some(platform_name) = extract_platform_name(line) {
                platforms.push(PlatformInfo {
                    name: platform_name,
                    r#type: "ROM".to_string(),
                });
            }
        }
    }

    // Parse BIOS platforms
    for line in bios_section.lines() {
        let line = line.trim();
        if line.starts_with('"') && line.contains("] =") {
            if let Some(platform_name) = extract_platform_name(line) {
                platforms.push(PlatformInfo {
                    name: platform_name,
                    r#type: "BIOS".to_string(),
                });
            }
        }
    }

    Ok(platforms)
}

fn extract_section(content: &str, section_name: &str) -> String {
    let start_marker = format!("[{}]", section_name);
    if let Some(start_pos) = content.find(&start_marker) {
        let remaining = &content[start_pos + start_marker.len()..];
        if let Some(end_pos) = remaining.find("\n\n") {
            return remaining[..end_pos].to_string();
        }
        return remaining.to_string();
    }
    String::new()
}

fn extract_platform_name(line: &str) -> Option<String> {
    // Extract platform name from lines like: "nes" = { ... }
    if let Some(start) = line.find('"') {
        if let Some(end) = line[start + 1..].find('"') {
            return Some(line[start + 1..start + 1 + end].to_string());
        }
    }
    None
}

#[tauri::command]
async fn download_collection(
    collection: String,
    platforms: Vec<String>,
    output_dir: String
) -> Result<String, String> {
    println!("Starting generation for collection: {}, platforms: {:?}, output_dir: {}",
             collection, platforms, output_dir);

    // Use Rust backend generator to produce URL files and optionally README
    let coll_path = format!("collections/{}.toml", collection);

    // Setup a simple cache manager next to the collection (expiry 24h)
    let cache = CacheManager::new(std::path::Path::new(".cache"), 24);

    // Generate URLs asynchronously
    let urls_ok = generate_collection_urls_async(&coll_path, Some(cache.clone()), false).await;

    if !urls_ok {
        return Err(format!("URL generation failed for {}", collection));
    }

    // Generate README synchronously (blocking call executed on background thread by Tauri)
    let readme_ok = tokio::task::spawn_blocking(move || generate_readme_sync(&coll_path, false)).await
        .map_err(|e| format!("Failed to join readme task: {}", e))?;

    if !readme_ok {
        return Err(format!("README generation failed for {}", collection));
    }

    Ok(format!("Generation completed for {} ({} platforms)", collection, platforms.len()))
}

#[tauri::command]
async fn select_folder() -> Result<String, String> {
    // For now, return default Downloads directory
    // In production, you'd use Tauri's native dialog API
    if let Some(home_dir) = dirs::home_dir() {
        let downloads = home_dir.join("Downloads");
        Ok(downloads.to_string_lossy().to_string())
    } else {
        Ok("/home/user/Downloads".to_string())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![
        get_collections,
        get_platforms,
        download_collection,
        select_folder
    ])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
