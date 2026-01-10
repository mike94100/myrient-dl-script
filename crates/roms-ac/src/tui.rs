use std::io;
use std::path::PathBuf;
use ratatui::{
    backend::CrosstermBackend,
    layout::{Constraint, Direction, Layout, Position, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Borders, List, ListItem, ListState, Paragraph, Wrap, Block},
    Frame, Terminal,
};
use crossterm::{
    event::{self, DisableBracketedPaste, DisableMouseCapture, EnableBracketedPaste, EnableMouseCapture, Event, KeyCode, KeyEvent, KeyModifiers, MouseButton, MouseEvent, MouseEventKind},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen, size},
};
use tui_textarea::{TextArea, Input};
use anyhow::Result;
use urlencoding;
use std::collections::HashMap;

#[derive(Clone, PartialEq)]
pub enum AppState {
    FileSelect,
    Editor,
}

#[derive(Clone, PartialEq)]
pub enum ViewMode {
    EditorOnly,
    PlatformsOnly,
    Both,
}

#[derive(Clone, PartialEq)]
enum HelpType {
    Editor,
    FileBrowser,
}

#[derive(Clone, PartialEq)]
pub enum Focus {
    Platforms,
    Editor,
}

#[derive(Clone)]
pub enum FileStatus {
    Unchanged,
    PendingEdits,
    Saved,
}

#[derive(Clone)]
pub struct FileEntry {
    pub path: PathBuf,
    pub is_dir: bool,
    pub name: String,
}

pub struct App {
    pub should_quit: bool,
    pub state: AppState,
    pub current_dir: PathBuf,
    pub file_entries: Vec<FileEntry>,
    pub file_list_state: ListState,
    pub selected_file: Option<PathBuf>,
    pub textarea: TextArea<'static>,
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
}

impl App {
    pub fn new() -> Result<Self> {
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

        // Load files in the collections directory
        let file_entries = Self::load_directory_contents(&collections_dir)?;

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
            textarea: TextArea::default(),
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
        })
    }

    fn load_directory_contents(dir_path: &PathBuf) -> Result<Vec<FileEntry>> {
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

    pub fn run(&mut self) -> Result<()> {
        // Setup terminal
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        execute!(stdout, EnterAlternateScreen, EnableBracketedPaste)?;
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
            LeaveAlternateScreen,
            DisableMouseCapture,
            DisableBracketedPaste
        )?;
        terminal.show_cursor()?;

        Ok(())
    }

    fn ui(&self, f: &mut Frame) {
        match self.state {
            AppState::FileSelect => self.draw_file_selector(f),
            AppState::Editor => self.draw_editor(f),
        }
    }

    fn draw_file_selector(&self, f: &mut Frame) {
        let area = f.area();

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Min(3), Constraint::Max(94), Constraint::Min(3)])
            .split(area);

        // Current directory path
        let dir_display = format!("Current Directory: {}", self.current_dir.display());
        let dir_title = Paragraph::new(dir_display)
            .style(Style::default().fg(Color::Cyan))
            .alignment(ratatui::layout::Alignment::Center);
        f.render_widget(dir_title, chunks[0]);

        // File list
        let items: Vec<ListItem> = self.file_entries
            .iter()
            .map(|entry| {
                let style = if entry.is_dir {
                    Style::default().fg(Color::Blue)
                } else {
                    Style::default().fg(Color::White)
                };
                ListItem::new(entry.name.clone()).style(style)
            })
            .collect();

        let list = List::new(items)
            .block(Block::default().borders(Borders::ALL).title("Files & Directories"))
            .highlight_style(Style::default().fg(Color::Blue))
            .highlight_symbol("▶ ");

        f.render_stateful_widget(list, chunks[1], &mut self.file_list_state.clone());

        // Help bar
        self.draw_help(f, chunks[2], HelpType::FileBrowser);
    }

    fn draw_editor(&self, f: &mut Frame) {
        let area = f.area();

        match self.view_mode {
            ViewMode::EditorOnly => {
                // Editor only: full screen editor + help
                let chunks = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([Constraint::Max(97), Constraint::Min(3)])
                    .split(area);

                self.draw_collection_editor(f, chunks[0]);
                self.draw_help(f, chunks[1], HelpType::Editor);
            }
            ViewMode::PlatformsOnly => {
                // Platforms only: platforms + URL viewer + help
                let chunks = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([Constraint::Max(97), Constraint::Min(3)])
                    .split(area);

                let content_chunks = Layout::default()
                    .direction(Direction::Horizontal)
                    .constraints([Constraint::Percentage(15), Constraint::Fill(1)])
                    .split(chunks[0]);

                self.draw_platform_selector(f, content_chunks[0]);
                self.draw_url_viewer(f, content_chunks[1]);
                self.draw_help(f, chunks[1], HelpType::Editor);
            }
            ViewMode::Both => {
                // Both: editor + platforms + URL viewer + help
                let chunks = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([Constraint::Max(50), Constraint::Max(50), Constraint::Min(3)])
                    .split(area);

                self.draw_collection_editor(f, chunks[0]);

                let content_chunks = Layout::default()
                    .direction(Direction::Horizontal)
                    .constraints([Constraint::Percentage(15), Constraint::Fill(1)])
                    .split(chunks[1]);

                self.draw_platform_selector(f, content_chunks[0]);
                self.draw_url_viewer(f, content_chunks[1]);
                self.draw_help(f, chunks[2], HelpType::Editor);
            }
        }
    }

    fn draw_collection_editor(&self, f: &mut Frame, area: Rect) {
        let border_color = match self.focus {
            Focus::Editor => Color::Cyan,
            Focus::Platforms => Color::White,
        };

        let status_str = match self.file_status {
            FileStatus::Unchanged => "- Unchanged",
            FileStatus::PendingEdits => "- Pending Edits",
            FileStatus::Saved => "- Saved",
        };

        let title = if let Some(ref msg) = self.save_message {
            format!("Collection Editor - {}", msg)
        } else {
            format!("Collection Editor {}", status_str)
        };

        let mut textarea = self.textarea.clone();
        textarea.set_block(
            Block::default()
                .title(title)
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color))
        );

        f.render_widget(&textarea, area);
    }

    fn draw_platform_selector(&self, f: &mut Frame, area: Rect) {
        let border_color = match self.focus {
            Focus::Editor => Color::White,
            Focus::Platforms => Color::Cyan,
        };
        let items: Vec<ListItem> = self.platform_entries
            .iter()
            .map(|platform| ListItem::new(platform.clone()))
            .collect();

        let list = List::new(items)
            .block(Block::default()
                .title("Platforms")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color)))
            .highlight_symbol("▶ ");

        f.render_stateful_widget(list, area, &mut self.platform_list_state.clone());
    }

    fn draw_url_viewer(&self, f: &mut Frame, area: Rect) {
        let title = if self.filtered_preview_mode {
            format!("URL List Viewer - Platform: {} (Filtered Preview)", self.selected_platform)
        } else {
            format!("URL List Viewer - Platform: {}", self.selected_platform)
        };

        let block = Block::default()
            .title(title)
            .borders(Borders::ALL)
            .style(Style::default().fg(Color::Green));

        let mut content = Vec::new();
        let inner_width = area.width.saturating_sub(2) as usize; // Subtract borders

        for line in &self.url_content {
            let wrapped_lines = Self::wrap_text_with_indent(line, inner_width, 2);
            for wrapped_line in wrapped_lines {
                content.push(Line::from(vec![Span::raw(wrapped_line)]));
            }
        }

        let paragraph = Paragraph::new(content)
            .block(block);

        f.render_widget(paragraph, area);
    }

    fn draw_help(&self, f: &mut Frame, area: Rect, help_type: HelpType) {
        let mouse_mode_str = if self.mouse_mode { "Mouse: ON" } else { "Mouse: OFF" };
        let view_mode_str = match self.view_mode {
            ViewMode::EditorOnly => "View: Editor",
            ViewMode::PlatformsOnly => "View: Platforms",
            ViewMode::Both => "View: Both",
        };
        
        let help_text = match help_type {
            HelpType::Editor => vec![
                Line::from(vec![
                    Span::styled("Esc", Style::default().fg(Color::Yellow)),
                    Span::styled(" back, ", Style::default().fg(Color::White)),
                    Span::styled("Tab", Style::default().fg(Color::Yellow)),
                    Span::styled(" switch focus, ", Style::default().fg(Color::White)),
                    Span::styled("F2", Style::default().fg(Color::Yellow)),
                    Span::styled(" toggle mouse", Style::default().fg(Color::White)),
                    Span::styled(" | ", Style::default().fg(Color::White)),
                    Span::styled(mouse_mode_str, Style::default().fg(Color::Cyan)),
                    Span::styled(", ", Style::default().fg(Color::White)),
                    Span::styled("F3", Style::default().fg(Color::Yellow)),
                    Span::styled(" toggle view", Style::default().fg(Color::White)),
                    Span::styled(" | ", Style::default().fg(Color::White)),
                    Span::styled(view_mode_str, Style::default().fg(Color::Magenta)),
                    Span::styled(", ", Style::default().fg(Color::White)),
                    Span::styled("Ctrl+S", Style::default().fg(Color::Yellow)),
                    Span::styled(" save", Style::default().fg(Color::White)),
                ]),
            ],
            HelpType::FileBrowser => vec![
                Line::from(vec![
                    Span::styled("↑↓", Style::default().fg(Color::Yellow)),
                    Span::styled(" navigate, ", Style::default().fg(Color::White)),
                    Span::styled("→/Enter", Style::default().fg(Color::Yellow)),
                    Span::styled(" enter dir/select file, ", Style::default().fg(Color::White)),
                    Span::styled("←", Style::default().fg(Color::Yellow)),
                    Span::styled(" go up, ", Style::default().fg(Color::White)),
                    Span::styled("Esc/q", Style::default().fg(Color::Yellow)),
                    Span::styled(" quit", Style::default().fg(Color::White)),
                ]),
            ],
        };

        let paragraph = Paragraph::new(help_text)
            .style(Style::default().fg(Color::White))
            .block(Block::default().borders(Borders::ALL));

        f.render_widget(paragraph, area);
    }

    fn wrap_text_with_indent(text: &str, width: usize, indent: usize) -> Vec<String> {
        let mut lines = Vec::new();
        let mut current_text = text.to_string();

        loop {
            if current_text.len() <= width {
                lines.push(current_text);
                break;
            }

            // Find the last space within width
            let cut_point = if let Some(space_pos) = current_text[..width].rfind(' ') {
                space_pos
            } else {
                width
            };

            lines.push(current_text[..cut_point].to_string());
            current_text = current_text[cut_point..].trim_start().to_string();

            if !current_text.is_empty() {
                // Add indentation for continuation lines
                let indent_str = " ".repeat(indent);
                current_text = indent_str + &current_text;
            } else {
                break;
            }
        }

        lines
    }

    fn handle_file_select_input(&mut self, key: KeyEvent) {
        match key.code {
            KeyCode::Char('q') | KeyCode::Esc => self.should_quit = true,
            KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => self.should_quit = true,
            KeyCode::F(2) => {
                self.mouse_mode = !self.mouse_mode;
                if self.mouse_mode {
                    execute!(std::io::stdout(), EnableMouseCapture).ok();
                } else {
                    execute!(std::io::stdout(), DisableMouseCapture).ok();
                }
                return;
            }
            KeyCode::Up => {
                let i = match self.file_list_state.selected() {
                    Some(i) => if i > 0 { i - 1 } else { 0 }, // Don't loop, stay at top
                    None => 0,
                };
                self.file_list_state.select(Some(i));
            }
            KeyCode::Down => {
                let i = match self.file_list_state.selected() {
                    Some(i) => if i < self.file_entries.len() - 1 { i + 1 } else { i }, // Don't loop, stay at bottom
                    None => 0,
                };
                self.file_list_state.select(Some(i));
            }
            KeyCode::Right | KeyCode::Enter => {
                if let Some(selected) = self.file_list_state.selected() {
                    if let Some(entry) = self.file_entries.get(selected) {
                        if entry.is_dir {
                            // Navigate to directory
                            if let Ok(new_entries) = Self::load_directory_contents(&entry.path) {
                                self.current_dir = entry.path.clone();
                                self.file_entries = new_entries;
                                self.file_list_state.select(Some(0));
                            }
                        } else {
                            // Select file
                            self.selected_file = Some(entry.path.clone());
                            // Load the collection file into textarea
                            if let Ok(content) = std::fs::read_to_string(&entry.path) {
                                self.original_content = content.clone();
                                self.textarea = TextArea::from(content.lines());
                                self.file_status = FileStatus::Unchanged;
                                self.save_message = None;
                                // Load platforms from TOML
                                if let Ok((filter, nofilter)) = crate::toml_utils::discover_and_organize_platforms(&entry.path.to_string_lossy()) {
                                    self.platform_entries = [filter, nofilter].concat();
                                    self.platform_entries.sort();
                                    if !self.platform_entries.is_empty() {
                                        self.platform_list_state.select(Some(0));
                                        self.selected_platform = self.platform_entries[0].clone();
                                    }
                                }
                                // Load actual URL content for the current platform
                                self.update_url_content_for_platform();
                            }
                            self.state = AppState::Editor;
                        }
                    }
                }
            }
            KeyCode::Left => {
                // Go up a directory (same as selecting "..")
                if let Some(parent) = self.current_dir.parent() {
                    if let Ok(new_entries) = Self::load_directory_contents(&parent.to_path_buf()) {
                        self.current_dir = parent.to_path_buf();
                        self.file_entries = new_entries;
                        self.file_list_state.select(Some(0));
                    }
                }
            }
            _ => {}
        }
    }

    fn handle_editor_input(&mut self, key: KeyEvent) {
        // Handle global key bindings
        match key.code {
            KeyCode::Esc => {
                // Go back to file selector
                self.state = AppState::FileSelect;
                return;
            }
            KeyCode::Tab => {
                // Switch focus based on view mode
                match self.view_mode {
                    ViewMode::EditorOnly => {
                        // Focus stays on editor
                    }
                    ViewMode::PlatformsOnly => {
                        // Focus stays on platforms
                    }
                    ViewMode::Both => {
                        // Switch between editor and platforms
                        self.focus = match self.focus {
                            Focus::Platforms => Focus::Editor,
                            Focus::Editor => Focus::Platforms,
                        };
                    }
                }
                return;
            }
            KeyCode::F(3) => {
                self.view_mode = match self.view_mode {
                    ViewMode::Both => {
                        self.focus = Focus::Editor;
                        ViewMode::EditorOnly
                    }
                    ViewMode::EditorOnly => {
                        self.focus = Focus::Platforms;
                        ViewMode::PlatformsOnly
                    }
                    ViewMode::PlatformsOnly => ViewMode::Both,
                };
                return;
            }
            KeyCode::F(2) => {
                self.mouse_mode = !self.mouse_mode;
                if self.mouse_mode {
                    execute!(std::io::stdout(), EnableMouseCapture).ok();
                } else {
                    execute!(std::io::stdout(), DisableMouseCapture).ok();
                }
                return;
            }
            KeyCode::Char('r') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                // Refresh filtering preview for all platforms
                self.refresh_filtering_preview();
                return;
            }
            KeyCode::Char('s') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                // Save the collection file with edited content
                if let Some(selected_file) = &self.selected_file {
                    let content = self.textarea.lines().join("\n");
                    if let Err(_e) = std::fs::write(selected_file, &content) {
                        self.save_message = Some("Save failed!".to_string());
                    } else {
                        self.original_content = content;
                        self.file_status = FileStatus::Saved;
                        // Save all current URL displays to files
                        self.save_all_url_lists();
                    }
                }
                return;
            }
            _ => {}
        }

        // Handle navigation based on focus
        match self.focus {
            Focus::Platforms => match key.code {
                KeyCode::Up => {
                    let i = match self.platform_list_state.selected() {
                        Some(i) => if i > 0 { i - 1 } else { 0 },
                        None => 0,
                    };
                    self.platform_list_state.select(Some(i));
                    if let Some(platform) = self.platform_entries.get(i) {
                        self.selected_platform = platform.clone();
                        if self.filtered_preview_mode {
                            self.update_current_url_display();
                        } else {
                            self.update_url_content_for_platform();
                        }
                    }
                    return;
                }
                KeyCode::Down => {
                    let i = match self.platform_list_state.selected() {
                        Some(i) => if i < self.platform_entries.len() - 1 { i + 1 } else { i },
                        None => 0,
                    };
                    self.platform_list_state.select(Some(i));
                    if let Some(platform) = self.platform_entries.get(i) {
                        self.selected_platform = platform.clone();
                        if self.filtered_preview_mode {
                            self.update_current_url_display();
                        } else {
                            self.update_url_content_for_platform();
                        }
                    }
                    return;
                }
                _ => {} // Other keys ignored when focus is on platforms
            },
            Focus::Editor => {
                // Handle text editor key bindings
                match key.code {
                    _ => {}
                }

                // Forward all other key events to the textarea for text editing
                let input = Input::from(key);
                let old_content = self.textarea.lines().join("\n");
                self.textarea.input(input);
                let new_content = self.textarea.lines().join("\n");

                // Update file status based on content changes
                if old_content != new_content {
                    self.save_message = None; // Clear save message when content changes
                    if new_content == self.original_content {
                        self.file_status = FileStatus::Unchanged;
                    } else {
                        match self.file_status {
                            FileStatus::Unchanged | FileStatus::PendingEdits => {
                                self.file_status = FileStatus::PendingEdits;
                            }
                            FileStatus::Saved => {
                                self.file_status = FileStatus::PendingEdits;
                            }
                        }
                    }
                }
            }
        }
    }

    fn extract_filename_from_url(url: &str) -> String {
        // Extract filename from URL
        let encoded_filename = url.split('/').last().unwrap_or(url);
        // URL decode the filename
        let decoded_filename = urlencoding::decode(encoded_filename).unwrap_or_else(|_| encoded_filename.into());
        // Remove file extension
        if let Some(dot_pos) = decoded_filename.rfind('.') {
            decoded_filename[..dot_pos].to_string()
        } else {
            decoded_filename.to_string()
        }
    }

    fn refresh_filtering_preview(&mut self) {
        if let Some(selected_file) = &self.selected_file {
            // Parse current editor content as TOML
            let toml_content = self.textarea.lines().join("\n");
            let filter = match crate::filters::CollectionFilter::new_from_content(&toml_content) {
                Ok(f) => f,
                Err(_) => {
                    self.save_message = Some("Invalid TOML!".to_string());
                    return;
                }
            };

            // Clear existing displays
            self.platform_url_displays.clear();

            // Process each platform sequentially (file I/O is fast enough)
            let selected_file_path = selected_file.to_string_lossy().to_string();

            for platform in &self.platform_entries {
                if let Ok((_, urls)) = Self::filter_platform_urls(&selected_file_path, platform.clone(), &filter) {
                    self.platform_url_displays.insert(platform.clone(), urls);
                }
            }

            // Update the filtered preview mode
            self.filtered_preview_mode = true;

            // Update current display for selected platform
            self.update_current_url_display();
        }
    }

    fn filter_platform_urls(collection_path: &str, platform: String, filter: &crate::filters::CollectionFilter) -> Result<(String, Vec<String>)> {
        // Load existing URL file
        let url_file_path = crate::toml_utils::get_url_file_path(&collection_path, &platform);
        let all_urls = if url_file_path.exists() {
            std::fs::read_to_string(&url_file_path).unwrap_or_default()
                .lines()
                .filter(|line| !line.trim().is_empty())
                .map(|line| line.to_string())
                .collect::<Vec<String>>()
        } else {
            Vec::new()
        };

        // Decode URLs to get titles for filtering (like the generator does)
        let titles: Vec<String> = all_urls.iter()
            .map(|url| Self::extract_filename_from_url(url))
            .collect();

        // Apply filters to titles
        let filtered_titles = filter.filter_files(&platform, &titles);

        // Map back to URLs with # prefixes for excluded ones
        let url_map: std::collections::HashMap<&str, &String> = titles.iter().map(|s| s.as_str()).zip(all_urls.iter()).collect();
        let filtered_urls: Vec<String> = filtered_titles.into_iter().map(|title| {
            if title.starts_with('#') {
                let clean_title = &title[1..];
                if let Some(&url) = url_map.get(clean_title) {
                    format!("#{}", url)
                } else {
                    title
                }
            } else {
                if let Some(&url) = url_map.get(title.as_str()) {
                    url.clone()
                } else {
                    title
                }
            }
        }).collect();

        // Convert to display format (filenames with status indicators)
        let display_urls = filtered_urls.into_iter().take(10).map(|url| {
            let filename = Self::extract_filename_from_url(&url);
            if url.starts_with('#') {
                format!("✗ {}", filename)
            } else {
                format!("✓ {}", filename)
            }
        }).collect();

        Ok((platform, display_urls))
    }

    fn update_current_url_display(&mut self) {
        if let Some(urls) = self.platform_url_displays.get(&self.selected_platform) {
            self.url_content = urls.clone();
        } else {
            self.url_content = Vec::new();
        }
    }

    fn save_all_url_lists(&mut self) {
        if let Some(selected_file) = &self.selected_file {
            for (platform, urls) in &self.platform_url_displays {
                let url_file_path = crate::toml_utils::get_url_file_path(&selected_file.to_string_lossy(), platform);
                // Convert display format back to URL format
                let url_lines: Vec<String> = urls.iter().map(|display_line| {
                    if display_line.starts_with("✗ ") {
                        format!("#{}", display_line[4..].to_string()) // Skip "✗ " and add #
                    } else if display_line.starts_with("✓ ") {
                        display_line[4..].to_string() // Skip "✓ "
                    } else {
                        display_line.clone()
                    }
                }).collect();

                let _ = std::fs::write(&url_file_path, url_lines.join("\n"));
            }
            // Reset to original mode after saving
            self.filtered_preview_mode = false;
        }
    }

    fn handle_mouse_input(&mut self, mouse_event: MouseEvent) {
        if mouse_event.kind != MouseEventKind::Down(MouseButton::Left) {
            return;
        }

        let (term_width, term_height) = size().unwrap_or((80, 24));
        let area = Rect::new(0, 0, term_width, term_height);

        match self.state {
            AppState::FileSelect => {
                let chunks = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([Constraint::Min(3), Constraint::Max(94), Constraint::Min(3)])
                    .split(area);
                let file_list_rect = chunks[1];

                if file_list_rect.contains(Position::new(mouse_event.column, mouse_event.row)) {
                    let item_index = (mouse_event.row as usize).saturating_sub(file_list_rect.y as usize + 1);
                    if item_index < self.file_entries.len() {
                        self.file_list_state.select(Some(item_index));
                        // Perform Enter action
                        if let Some(entry) = self.file_entries.get(item_index) {
                            if entry.is_dir {
                                if let Ok(new_entries) = Self::load_directory_contents(&entry.path) {
                                    self.current_dir = entry.path.clone();
                                    self.file_entries = new_entries;
                                    self.file_list_state.select(Some(0));
                                }
                            } else {
                                self.selected_file = Some(entry.path.clone());
                                if let Ok(content) = std::fs::read_to_string(&entry.path) {
                                    self.original_content = content.clone();
                                    self.textarea = TextArea::from(content.lines());
                                    self.file_status = FileStatus::Unchanged;
                                    self.save_message = None;
                                    if let Ok((filter, nofilter)) = crate::toml_utils::discover_and_organize_platforms(&entry.path.to_string_lossy()) {
                                        self.platform_entries = [filter, nofilter].concat();
                                        self.platform_entries.sort();
                                        if !self.platform_entries.is_empty() {
                                            self.platform_list_state.select(Some(0));
                                            self.selected_platform = self.platform_entries[0].clone();
                                        }
                                    }
                                    self.update_url_content_for_platform();
                                }
                                self.state = AppState::Editor;
                            }
                        }
                    }
                }
            }
            AppState::Editor => {
                match self.view_mode {
                    ViewMode::EditorOnly => {
                        // No mouse handling in editor-only mode
                    }
                    ViewMode::PlatformsOnly => {
                        let chunks = Layout::default()
                            .direction(Direction::Vertical)
                            .constraints([Constraint::Max(97), Constraint::Min(3)])
                            .split(area);
                        let content_chunks = Layout::default()
                            .direction(Direction::Horizontal)
                            .constraints([Constraint::Percentage(15), Constraint::Fill(1)])
                            .split(chunks[0]);
                        let platform_rect = content_chunks[0];

                        if platform_rect.contains(Position::new(mouse_event.column, mouse_event.row)) {
                            let item_index = (mouse_event.row as usize).saturating_sub(platform_rect.y as usize + 1);
                            if item_index < self.platform_entries.len() {
                                self.platform_list_state.select(Some(item_index));
                                if let Some(platform) = self.platform_entries.get(item_index) {
                                    self.selected_platform = platform.clone();
                                    if self.filtered_preview_mode {
                                        self.update_current_url_display();
                                    } else {
                                        self.update_url_content_for_platform();
                                    }
                                }
                            }
                        }
                    }
                    ViewMode::Both => {
                        let chunks = Layout::default()
                            .direction(Direction::Vertical)
                            .constraints([Constraint::Max(50), Constraint::Max(50), Constraint::Min(3)])
                            .split(area);
                        let content_chunks = Layout::default()
                            .direction(Direction::Horizontal)
                            .constraints([Constraint::Percentage(15), Constraint::Fill(1)])
                            .split(chunks[1]);
                        let platform_rect = content_chunks[0];

                        if platform_rect.contains(Position::new(mouse_event.column, mouse_event.row)) {
                            let item_index = (mouse_event.row as usize).saturating_sub(platform_rect.y as usize + 1);
                            if item_index < self.platform_entries.len() {
                                self.platform_list_state.select(Some(item_index));
                                if let Some(platform) = self.platform_entries.get(item_index) {
                                    self.selected_platform = platform.clone();
                                    if self.filtered_preview_mode {
                                        self.update_current_url_display();
                                    } else {
                                        self.update_url_content_for_platform();
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    fn update_url_content_for_platform(&mut self) {
        // Try to load actual URL content for the selected platform from TOML
        if let Some(selected_file) = &self.selected_file {
            let url_file_path = crate::toml_utils::get_url_file_path(&selected_file.to_string_lossy(), &self.selected_platform);
            if url_file_path.exists() {
                if let Ok(content) = std::fs::read_to_string(&url_file_path) {
                    // Parse current TOML to get actual filters
                    let toml_content = self.textarea.lines().join("\n");
                    if let Ok(filter) = crate::filters::CollectionFilter::new_from_content(&toml_content) {
                        // Get all URLs from file (including commented ones)
                        let all_urls: Vec<String> = content.lines()
                            .filter(|line| !line.trim().is_empty())
                            .map(|line| line.to_string())
                            .collect();

                        // Decode URLs to get titles for filtering (like the generator does)
                        let titles: Vec<String> = all_urls.iter()
                            .map(|url| Self::extract_filename_from_url(url))
                            .collect();

                        // Apply filters to titles
                        let filtered_titles = filter.filter_files(&self.selected_platform, &titles);

                        // Map back to URLs with # prefixes for excluded ones
                        let url_map: std::collections::HashMap<&str, &String> = titles.iter().map(|s| s.as_str()).zip(all_urls.iter()).collect();
                        let filtered_urls: Vec<String> = filtered_titles.into_iter().map(|title| {
                            if title.starts_with('#') {
                                let clean_title = &title[1..];
                                if let Some(&url) = url_map.get(clean_title) {
                                    format!("#{}", url)
                                } else {
                                    title
                                }
                            } else {
                                if let Some(&url) = url_map.get(title.as_str()) {
                                    url.clone()
                                } else {
                                    title
                                }
                            }
                        }).collect();

                        // Convert to display format
                        self.url_content = filtered_urls.into_iter().take(10).map(|url| {
                            let filename = Self::extract_filename_from_url(&url);
                            if url.starts_with('#') {
                                format!("✗ {}", filename)
                            } else {
                                format!("✓ {}", filename)
                            }
                        }).collect();
                    } else {
                        // Fallback if TOML parsing fails - show all as included
                        let urls: Vec<String> = content.lines()
                            .filter(|line| !line.trim().is_empty())
                            .map(|line| line.to_string())
                            .collect();

                        self.url_content = urls.into_iter().take(10).map(|url| {
                            let filename = Self::extract_filename_from_url(&url);
                            format!("✓ {}", filename)
                        }).collect();
                    }
                }
            }
        }
    }
}
