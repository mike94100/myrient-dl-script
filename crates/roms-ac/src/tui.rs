use std::io;
use std::path::PathBuf;
use ratatui::{
    backend::CrosstermBackend,
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Borders, List, ListItem, ListState, Paragraph, Wrap, Block},
    Frame, Terminal,
};
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyEvent, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use tui_textarea::{TextArea, Input};
use anyhow::Result;
use urlencoding;

#[derive(Clone)]
pub enum AppState {
    FileSelect,
    Editor,
}

#[derive(Clone)]
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
        execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
        let backend = CrosstermBackend::new(stdout);
        let mut terminal = Terminal::new(backend)?;

        // Run the main loop
        loop {
            terminal.draw(|f| self.ui(f))?;

            if let Event::Key(key) = event::read()? {
                match self.state {
                    AppState::FileSelect => self.handle_file_select_input(key),
                    AppState::Editor => self.handle_editor_input(key),
                }
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
            DisableMouseCapture
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
            .constraints([Constraint::Min(3), Constraint::Min(5), Constraint::Length(1)])
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
            .highlight_style(Style::default().bg(Color::Blue).fg(Color::White))
            .highlight_symbol("▶ ");

        f.render_stateful_widget(list, chunks[1], &mut self.file_list_state.clone());

        // Help bar
        self.draw_file_browser_help(f, chunks[2]);
    }

    fn draw_editor(&self, f: &mut Frame) {
        let area = f.area();

        // Create main layout with three sections: editor, platform/url viewer, help
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Percentage(45), Constraint::Percentage(45), Constraint::Length(3)])
            .split(area);

        // Top: Collection Editor (full width)
        self.draw_collection_editor(f, chunks[0]);

        // Middle: split horizontally for platform selector and URL viewer
        let middle_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(25), Constraint::Percentage(75)])
            .split(chunks[1]);

        // Left panel: Platform Selector
        self.draw_platform_selector(f, middle_chunks[0]);

        // Right panel: URL List Viewer
        self.draw_url_viewer(f, middle_chunks[1]);

        // Bottom: Help bar
        self.draw_help_bar(f, chunks[2]);
    }

    fn draw_collection_editor(&self, f: &mut Frame, area: Rect) {
        let border_color = match self.focus {
            Focus::Editor => Color::Yellow,
            Focus::Platforms => Color::Cyan,
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
            Focus::Platforms => Color::Yellow,
            Focus::Editor => Color::White,
        };

        let items: Vec<ListItem> = self.platform_entries
            .iter()
            .map(|platform| ListItem::new(platform.clone()))
            .collect();

        let list = List::new(items)
            .block(Block::default().borders(Borders::ALL).title("Platforms").border_style(Style::default().fg(border_color)))
            .highlight_style(Style::default().bg(Color::Blue).fg(Color::White))
            .highlight_symbol("▶ ");

        f.render_stateful_widget(list, area, &mut self.platform_list_state.clone());
    }

    fn draw_url_viewer(&self, f: &mut Frame, area: Rect) {
        let block = Block::default()
            .title(format!("URL List Viewer - Platform: {}", self.selected_platform))
            .borders(Borders::ALL)
            .style(Style::default().fg(Color::Green));

        let content = self.url_content
            .iter()
            .map(|line| Line::from(vec![Span::raw(line)]))
            .collect::<Vec<_>>();

        let paragraph = Paragraph::new(content)
            .block(block)
            .wrap(Wrap { trim: true });

        f.render_widget(paragraph, area);
    }

    fn draw_help_bar(&self, f: &mut Frame, area: Rect) {
        let help_text = vec![
            Line::from(vec![
                Span::styled("Esc", Style::default().fg(Color::Yellow)),
                Span::styled(" back to files, ", Style::default().fg(Color::White)),
                Span::styled("Tab", Style::default().fg(Color::Yellow)),
                Span::styled(" switch focus, ", Style::default().fg(Color::White)),
                Span::styled("Ctrl+S", Style::default().fg(Color::Yellow)),
                Span::styled(" save", Style::default().fg(Color::White)),
            ]),
        ];

        let paragraph = Paragraph::new(help_text)
            .style(Style::default().bg(Color::Blue).fg(Color::White));

        f.render_widget(paragraph, area);
    }

    fn draw_file_browser_help(&self, f: &mut Frame, area: Rect) {
        let help_text = Line::from(vec![
            Span::styled("↑↓", Style::default().fg(Color::Yellow)),
            Span::styled(" navigate, ", Style::default().fg(Color::White)),
            Span::styled("→/Enter", Style::default().fg(Color::Yellow)),
            Span::styled(" enter dir/select file, ", Style::default().fg(Color::White)),
            Span::styled("←", Style::default().fg(Color::Yellow)),
            Span::styled(" go up, ", Style::default().fg(Color::White)),
            Span::styled("Esc/q", Style::default().fg(Color::Yellow)),
            Span::styled(" quit", Style::default().fg(Color::White)),
        ]);

        let paragraph = Paragraph::new(help_text)
            .style(Style::default().bg(Color::Blue).fg(Color::White));

        f.render_widget(paragraph, area);
    }

    fn handle_file_select_input(&mut self, key: KeyEvent) {
        match key.code {
            KeyCode::Char('q') | KeyCode::Esc => self.should_quit = true,
            KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => self.should_quit = true,
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
                // Switch focus
                self.focus = match self.focus {
                    Focus::Platforms => Focus::Editor,
                    Focus::Editor => Focus::Platforms,
                };
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
                        self.update_url_content_for_platform();
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
                        self.update_url_content_for_platform();
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

    fn update_url_content_for_platform(&mut self) {
        // Try to load actual URL content for the selected platform from TOML
        if let Some(selected_file) = &self.selected_file {
            let url_file_path = crate::toml_utils::get_url_file_path(&selected_file.to_string_lossy(), &self.selected_platform);
            if url_file_path.exists() {
                if let Ok(content) = std::fs::read_to_string(&url_file_path) {
                    // Parse and filter URLs based on collection filters
                    let urls: Vec<String> = content.lines()
                        .filter(|line| !line.trim().is_empty() && !line.starts_with('#'))
                        .map(|line| line.to_string())
                        .collect();

                    // For now, just show first 10 URLs with some sample filtering
                    self.url_content = urls.into_iter().take(10).map(|url| {
                        let filename = Self::extract_filename_from_url(&url);
                        // Simple demo filtering - in a real implementation this would use the actual filters
                        if url.contains("Japan") {
                            format!("✗ {}", filename)
                        } else {
                            format!("✓ {}", filename)
                        }
                    }).collect();
                }
            }
        }
    }
}
