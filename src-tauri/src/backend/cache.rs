use std::collections::HashMap;
use std::fs::{self, File};
use std::io::prelude::*;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::Result;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct CacheEntry {
    url: String,
    content: String,
    timestamp: u64,
}

#[derive(Clone)]
pub struct CacheManager {
    cache_dir: PathBuf,
    expiry_hours: u64,
}

impl CacheManager {
    pub fn new<P: AsRef<Path>>(cache_dir: P, expiry_hours: u64) -> Self {
        let dir = cache_dir.as_ref().to_path_buf();
        let _ = fs::create_dir_all(&dir);
        CacheManager { cache_dir: dir, expiry_hours }
    }

    fn cache_key(&self, url: &str) -> String {
        use md5::{Digest, Md5};
        let mut hasher = Md5::new();
        hasher.update(url.as_bytes());
        format!("{:x}", hasher.finalize())
    }

    fn cache_path(&self, key: &str) -> PathBuf {
        self.cache_dir.join(format!("{}.json", key))
    }

    fn is_expired(&self, path: &Path) -> bool {
        if !path.exists() {
            return true;
        }
        if let Ok(metadata) = fs::metadata(path) {
            if let Ok(mtime) = metadata.modified() {
                if let Ok(duration) = mtime.duration_since(UNIX_EPOCH) {
                    let age_secs = std::time::SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0) - duration.as_secs();
                    let age_hours = age_secs as f64 / 3600.0;
                    return age_hours > (self.expiry_hours as f64);
                }
            }
        }
        false
    }

    pub fn get(&self, url: &str) -> Option<String> {
        let key = self.cache_key(url);
        let path = self.cache_path(&key);
        if self.is_expired(&path) {
            return None;
        }
        match fs::read_to_string(&path) {
            Ok(s) => {
                match serde_json::from_str::<CacheEntry>(&s) {
                    Ok(entry) => Some(entry.content),
                    Err(_) => None,
                }
            }
            Err(_) => None,
        }
    }

    pub fn put(&self, url: &str, content: &str) -> Result<()> {
        let key = self.cache_key(url);
        let path = self.cache_path(&key);
        let entry = CacheEntry {
            url: url.to_string(),
            content: content.to_string(),
            timestamp: SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs(),
        };
        let json = serde_json::to_string_pretty(&entry)?;
        let mut file = File::create(&path)?;
        file.write_all(json.as_bytes())?;
        Ok(())
    }

    pub fn clear(&self) -> Result<()> {
        for entry in fs::read_dir(&self.cache_dir)? {
            let p = entry?.path();
            if p.extension().and_then(|s| s.to_str()) == Some("json") {
                let _ = fs::remove_file(p);
            }
        }
        Ok(())
    }
}
