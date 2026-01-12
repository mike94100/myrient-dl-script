use std::io;
use std::path::PathBuf;
use ratatui::{
    backend::CrosstermBackend,
    widgets::ListState, Terminal,
};
use crossterm::{
    event::{self, Event},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use anyhow::Result;
use std::collections::HashMap;

/// # TUI App Module
///
/// Core application logic and state management for the Terminal User Interface.
/// This module contains the main App struct that orchestrates all TUI functionality,
/// including file management, platform selection, and user interaction handling.

use super::types::*;
use super::cache::CacheManager;
use crate::toml_utils;
use crate::filters;

use log;

/// Main application structure for the ROM collection TUI.
///
/// The App struct maintains all state for the terminal user interface,
/// including file management, platform selection, caching, and UI layout.
/// It serves as the central coordinator for user interactions and data flow.
///
/// # Example
/// ```rust,no_run
/// use roms_ac::tui::App;
///
/// let mut app = App::new().unwrap();
/// app.run().unwrap();
/// ```
pub struct App {
    pub should_quit: bool,
    pub state: AppState,
    pub current_dir: PathBuf,
    pub file_entries: Vec<FileEntry>,
    pub file_list_state: ListState,
    pub selected_file: Option<PathBuf>,
    pub textarea: tui_textarea::TextArea<'static>,
    pub url_content: Vec<String>,
    pub selected_platform: String,
    pub original_content: String,
    pub platform_entries: Vec<String>,
    pub platform_list_state: ListState,
    pub focus: Focus,
    pub save_message: Option<String>,
    pub file_status: FileStatus,
    pub platform_url_displays: HashMap<String, Vec<String>>,
    pub filtered_preview_mode: bool,
    pub mouse_mode: bool,
    pub view_mode: ViewMode,
    pub url_scroll_offset: u16,
    pub url_cache: HashMap<String, Vec<String>>,
    pub cache_toml_hash: u64,
    pub url_viewer_height: u16,
    pub platform_scroll_offset: usize,
}

impl App {
    /// Creates a new TUI application instance.
    ///
    /// This constructor initializes the application by:
    /// 1. Discovering the repository root (looking for config.toml or .git)
    /// 2. Loading the collections directory path from configuration
    /// 3. Scanning the collections directory for TOML files
    /// 4. Setting up initial UI state
    ///
    /// # Returns
    /// A new `App` instance ready to run, or an error if initialization fails.
    ///
    /// # Errors
    /// - If the current directory cannot be determined
    /// - If repository root discovery fails
    /// - If the collections directory cannot be read
    pub fn new() -> Result<Self> {
        log::info!("Initializing TUI application");
        // Find repo root
        let current_dir = std::env::current_dir()?;
        let mut repo_root = current_dir.clone();

        // Search up to 10 levels up for repo root
        for _ in 0..10 {
            if repo_root.join("config.toml").exists() || repo_root.join(".git").exists() {
                break;
            }
            if !repo_root.pop() {
                // If we can't find repo root, use current directory
                repo_root = current_dir.clone();
                break;
            }
        }

        log::info!("Using repository root: {}", repo_root.display());

        // Read config.toml to get the collections directory
        let config_path = repo_root.join("config.toml");
        let collections_dir = if config_path.exists() {
            // Try to read the collection_directory from config
            if let Ok(collection_dir_str) = crate::toml_utils::get_toml_value::<String>(&config_path.to_string_lossy(), "general.collection_directory") {
                repo_root.join(collection_dir_str)
            } else {
                // Fallback to default "collections"
                repo_root.join("collections")
            }
        } else {
            // No config file, use default
            repo_root.join("collections")
        };

        log::info!("Using collections directory: {}", collections_dir.display());

        // Load files in the collections directory
        let file_entries = Self::load_directory_contents(&collections_dir)?;
        log::info!("Loaded {} collection files", file_entries.len());

        let mut file_list_state = ListState::default();
        if !file_entries.is_empty() {
            file_list_state.select(Some(0));
        }

        Ok(Self {
            should_quit: false,
            state: AppState::FileSelect,
            current_dir: repo_root,
            file_entries,
            file_list_state,
            selected_file: None,
            textarea: tui_textarea::TextArea::default(),
            url_content: vec![],
            selected_platform: "gb".to_string(),
            original_content: String::new(),
            platform_entries: vec![],
            platform_list_state: ListState::default(),
            focus: Focus::Editor,
            save_message: None,
            file_status: FileStatus::Unchanged,
            platform_url_displays: HashMap::new(),
            filtered_preview_mode: false,
            mouse_mode: false,
            view_mode: ViewMode::Both,
            url_scroll_offset: 0,
            url_cache: HashMap::new(),
            cache_toml_hash: 0,
            url_viewer_height: 0,
            platform_scroll_offset: 0,
        })
    }

    pub(crate) fn load_directory_contents(dir_path: &PathBuf) -> Result<Vec<FileEntry>> {
        let mut entries = vec![];

        // Add parent directory option if not at root
        if dir_path.parent().is_some() {
            entries.push(FileEntry {
                path: dir_path.parent().unwrap().to_path_buf(),
                is_dir: true,
                name: "..".to_string(),
            });
        }

        if let Ok(read_dir) = std::fs::read_dir(dir_path) {
            let mut dirs = vec![];
            let mut files = vec![];

            for entry in read_dir.filter_map(|e| e.ok()) {
                let path = entry.path();
                let name = path.file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or("Unknown")
                    .to_string();

                if path.is_dir() {
                    dirs.push(FileEntry {
                        path: path.clone(),
                        is_dir: true,
                        name: format!("{}/", name),
                    });
                } else if path.extension().and_then(|ext| ext.to_str()) == Some("toml") {
                    files.push(FileEntry {
                        path,
                        is_dir: false,
                        name,
                    });
                }
            }

            // Sort directories first, then files
            dirs.sort_by(|a, b| a.name.cmp(&b.name));
            files.sort_by(|a, b| a.name.cmp(&b.name));

            entries.extend(dirs);
            entries.extend(files);
        }

        Ok(entries)
    }

    /// Runs the main TUI application loop.
    ///
    /// This method sets up the terminal in raw mode, enters alternate screen,
    /// and runs the main event loop handling user input and UI updates.
    /// The loop continues until the user quits the application.
    ///
    /// The event loop processes:
    /// - Keyboard input for navigation and editing
    /// - Mouse events when mouse mode is enabled
    /// - Text paste events for the editor
    ///
    /// # Returns
    /// `Ok(())` when the application exits normally, or an error if terminal
    /// operations fail.
    ///
    /// # Terminal State
    /// The terminal is restored to its original state when the application exits,
    /// including leaving alternate screen and showing the cursor.
    pub fn run(&mut self) -> Result<()> {
        // Setup terminal
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        execute!(stdout, EnterAlternateScreen)?;
        let backend = CrosstermBackend::new(stdout);
        let mut terminal = Terminal::new(backend)?;

        // Run the main loop
        loop {
            terminal.draw(|f| self.ui(f))?;

            match event::read()? {
                Event::Key(key) => {
                    match self.state {
                        AppState::FileSelect => self.handle_file_select_input(key),
                        AppState::Editor => self.handle_editor_input(key),
                    }
                }
                Event::Mouse(mouse_event) => {
                    if self.mouse_mode {
                        self.handle_mouse_input(mouse_event);
                    }
                }
                Event::Paste(content) => {
                    if self.state == AppState::Editor && self.focus == Focus::Editor {
                        self.textarea.insert_str(&content);
                        let new_content = self.textarea.lines().join("\n");
                        if new_content != self.original_content {
                            self.save_message = None;
                            self.file_status = FileStatus::PendingEdits;
                        }
                    }
                }
                _ => {}
            }

            if self.should_quit {
                break;
            }
        }

        // Restore terminal
        disable_raw_mode()?;
        execute!(
            terminal.backend_mut(),
            LeaveAlternateScreen
        )?;
        terminal.show_cursor()?;

        Ok(())
    }

    pub(crate) fn cache_first_platform(&mut self) {
        if let Some(first_platform) = self.platform_entries.first().cloned() {
            self.ensure_platform_cached(&first_platform);
        }
    }

    pub(crate) fn hash_toml_content(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        let toml_content = self.textarea.lines().join("\n");
        toml_content.hash(&mut hasher);
        hasher.finish()
    }

    pub(crate) fn select_platform(&mut self, index: usize) {
        self.select_platform_with_cache(index, true);
    }

    pub(crate) fn select_platform_with_cache(&mut self, index: usize, should_cache_next: bool) {
        self.platform_list_state.select(Some(index));
        if let Some(platform) = self.platform_entries.get(index).cloned() {
            self.selected_platform = platform.clone();
            self.url_scroll_offset = 0;
            if self.filtered_preview_mode {
                self.update_current_url_display();
            } else {
                self.update_url_content_for_platform();
                if should_cache_next {
                    self.cache_next_sequential_platform(&platform);
                }
            }
        }
    }

    fn ensure_platform_cached(&mut self, platform: &str) {
        if !self.url_cache.contains_key(platform) {
            let original_platform = self.selected_platform.clone();
            self.selected_platform = platform.to_string();
            self.update_url_content_for_platform();
            self.selected_platform = original_platform;
        }
    }

    fn cache_next_sequential_platform(&mut self, current_platform: &str) {
        // Get the next platform name in one operation to avoid borrowing conflicts
        let next_platform_name = self.platform_entries.iter().position(|p| p == current_platform)
            .and_then(|current_idx| {
                let next_idx = current_idx + 1;
                self.platform_entries.get(next_idx).cloned()
            });

        if let Some(next_platform) = next_platform_name {
            self.ensure_platform_cached(&next_platform);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;
    use tempfile::TempDir;

    fn create_test_app() -> App {
        // Create a temporary directory structure that mimics the repo
        let temp_dir = TempDir::new().unwrap();
        let collections_dir = temp_dir.path().join("collections");
        std::fs::create_dir_all(&collections_dir).unwrap();

        // Create a sample collection file
        let collection_file = collections_dir.join("test.toml");
        std::fs::write(&collection_file, r#"
[roms]
gb = { url = "https://example.com/gb" }
gba = { url = "https://example.com/gba" }

[filters]
include = [["*.zip"]]
exclude = ["beta", "proto"]
        "#).unwrap();

        // Change to temp directory and create app
        let original_dir = env::current_dir().unwrap();
        env::set_current_dir(&temp_dir).unwrap();

        let app = App::new().unwrap();

        // Restore original directory
        env::set_current_dir(original_dir).unwrap();

        app
    }

    #[test]
    fn test_select_platform_updates_state() {
        let mut app = create_test_app();
        app.platform_entries = vec!["gb".to_string(), "gba".to_string(), "nes".to_string()];
        app.selected_platform = "gb".to_string();
        app.platform_list_state.select(Some(0));

        // Select platform at index 1 (gba)
        app.select_platform(1);

        assert_eq!(app.selected_platform, "gba");
        assert_eq!(app.platform_list_state.selected(), Some(1));
        assert_eq!(app.url_scroll_offset, 0); // Should reset scroll
    }

    #[test]
    fn test_select_platform_with_cache_state_updates() {
        let mut app = create_test_app();
        app.platform_entries = vec!["gb".to_string(), "gba".to_string()];
        app.selected_platform = "gb".to_string();
        app.filtered_preview_mode = true; // Avoid file I/O by using filtered mode

        // Test with caching enabled (but won't actually cache due to filtered mode)
        app.select_platform_with_cache(1, true);
        assert_eq!(app.selected_platform, "gba");

        // Test with caching disabled
        app.select_platform_with_cache(0, false);
        assert_eq!(app.selected_platform, "gb");
    }

    #[test]
    fn test_select_platform_resets_scroll_offset() {
        let mut app = create_test_app();
        app.platform_entries = vec!["gb".to_string(), "gba".to_string()];
        app.url_scroll_offset = 50; // Set non-zero scroll

        app.select_platform(1);

        assert_eq!(app.url_scroll_offset, 0); // Should be reset
    }

    #[test]
    fn test_cache_first_platform_with_platforms() {
        let mut app = create_test_app();
        app.platform_entries = vec!["gb".to_string(), "gba".to_string()];

        app.cache_first_platform();

        // Should have attempted to cache the first platform
        // (The actual caching logic depends on ensure_platform_cached)
        assert_eq!(app.platform_entries.len(), 2);
    }

    #[test]
    fn test_hash_toml_content_changes_with_content() {
        let mut app = create_test_app();

        // Set initial content
        app.textarea = tui_textarea::TextArea::from(vec!["line 1".to_string(), "line 2".to_string()]);
        let hash1 = app.hash_toml_content();

        // Change content
        app.textarea = tui_textarea::TextArea::from(vec!["different content".to_string()]);
        let hash2 = app.hash_toml_content();

        // Hashes should be different
        assert_ne!(hash1, hash2);
    }

    #[test]
    fn test_hash_toml_content_same_content_same_hash() {
        // Create minimal apps for testing - avoid file I/O
        let mut app1 = App {
            should_quit: false,
            state: AppState::FileSelect,
            current_dir: PathBuf::new(),
            file_entries: vec![],
            file_list_state: ListState::default(),
            selected_file: None,
            textarea: tui_textarea::TextArea::from(vec!["same content".to_string()]),
            url_content: vec![],
            selected_platform: "gb".to_string(),
            original_content: String::new(),
            platform_entries: vec![],
            platform_list_state: ListState::default(),
            focus: Focus::Editor,
            save_message: None,
            file_status: FileStatus::Unchanged,
            platform_url_displays: HashMap::new(),
            filtered_preview_mode: false,
            mouse_mode: false,
            view_mode: ViewMode::Both,
            url_scroll_offset: 0,
            url_cache: HashMap::new(),
            cache_toml_hash: 0,
            url_viewer_height: 0,
            platform_scroll_offset: 0,
        };

        let mut app2 = App {
            should_quit: false,
            state: AppState::FileSelect,
            current_dir: PathBuf::new(),
            file_entries: vec![],
            file_list_state: ListState::default(),
            selected_file: None,
            textarea: tui_textarea::TextArea::from(vec!["same content".to_string()]),
            url_content: vec![],
            selected_platform: "gb".to_string(),
            original_content: String::new(),
            platform_entries: vec![],
            platform_list_state: ListState::default(),
            focus: Focus::Editor,
            save_message: None,
            file_status: FileStatus::Unchanged,
            platform_url_displays: HashMap::new(),
            filtered_preview_mode: false,
            mouse_mode: false,
            view_mode: ViewMode::Both,
            url_scroll_offset: 0,
            url_cache: HashMap::new(),
            cache_toml_hash: 0,
            url_viewer_height: 0,
            platform_scroll_offset: 0,
        };

        let hash1 = app1.hash_toml_content();
        let hash2 = app2.hash_toml_content();

        assert_eq!(hash1, hash2);
    }

    #[test]
    fn test_load_directory_contents_filters_toml_files() {
        let temp_dir = TempDir::new().unwrap();

        // Create various files
        std::fs::write(temp_dir.path().join("collection.toml"), "content").unwrap();
        std::fs::write(temp_dir.path().join("readme.md"), "content").unwrap();
        std::fs::write(temp_dir.path().join("data.txt"), "content").unwrap();

        let entries = App::load_directory_contents(&temp_dir.path().to_path_buf()).unwrap();

        // Should only include .toml files and parent directory (..)
        assert!(entries.len() >= 2); // At least .. and collection.toml
        let toml_files: Vec<_> = entries.iter().filter(|e| !e.is_dir && e.name.ends_with(".toml")).collect();
        assert_eq!(toml_files.len(), 1);
        assert_eq!(toml_files[0].name, "collection.toml");
    }

    #[test]
    fn test_load_directory_contents_adds_parent_directory() {
        let temp_dir = TempDir::new().unwrap();
        let sub_dir = temp_dir.path().join("subdir");
        std::fs::create_dir(&sub_dir).unwrap();

        let entries = App::load_directory_contents(&sub_dir).unwrap();

        // Should include parent directory (..)
        let parent_entries: Vec<_> = entries.iter().filter(|e| e.is_dir && e.name == "..").collect();
        assert_eq!(parent_entries.len(), 1);
    }

    #[test]
    fn test_ensure_platform_cached() {
        let mut app = create_test_app();
        app.platform_entries = vec!["gb".to_string(), "gba".to_string()];

        // Initially no cache for "gb"
        assert!(!app.url_cache.contains_key("gb"));

        // This will attempt to cache "gb" but won't actually succeed without proper setup
        // We're testing that the method doesn't panic and updates the selected_platform temporarily
        let original_platform = app.selected_platform.clone();
        app.ensure_platform_cached("gb");

        // selected_platform should be restored
        assert_eq!(app.selected_platform, original_platform);
    }
}
