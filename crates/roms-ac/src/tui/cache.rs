use std::fs::{self, File};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::Result;
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize)]
struct CacheEntry {
    url: String,
    content: String,
    timestamp: u64,
}

#[derive(Clone)]
pub struct CacheManager {
    dir: PathBuf,
    expiry_hours: u64,
}

impl CacheManager {
    pub fn new(dir: &Path, expiry_hours: u64) -> Self {
        let dir = dir.to_path_buf();
        let _ = fs::create_dir_all(&dir);
        CacheManager { dir, expiry_hours }
    }

    fn key(&self, url: &str) -> String {
        format!("{:x}", md5::compute(url))
    }

    fn path_for(&self, key: &str) -> PathBuf {
        self.dir.join(format!("{}.json", key))
    }

    fn is_expired(&self, p: &Path) -> bool {
        if !p.exists() { return true; }
        if let Ok(meta) = fs::metadata(p) {
            if let Ok(m) = meta.modified() {
                if let Ok(dur) = SystemTime::now().duration_since(m) {
                    return dur.as_secs() > (self.expiry_hours * 3600);
                }
            }
        }
        false
    }

    pub fn get(&self, url: &str) -> Option<String> {
        let key = self.key(url);
        let p = self.path_for(&key);
        if self.is_expired(&p) { return None; }
        let s = fs::read_to_string(&p).ok()?;
        let e: CacheEntry = serde_json::from_str(&s).ok()?;
        Some(e.content)
    }

    pub fn put(&self, url: &str, content: &str) -> Result<()> {
        let key = self.key(url);
        let p = self.path_for(&key);
        let entry = CacheEntry { url: url.to_string(), content: content.to_string(), timestamp: SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs() };
        let s = serde_json::to_string_pretty(&entry)?;
        let mut f = File::create(&p)?;
        f.write_all(s.as_bytes())?;
        Ok(())
    }
}
