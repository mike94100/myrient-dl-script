use crossterm::event::{KeyCode, KeyEvent, KeyModifiers, MouseButton, MouseEvent, MouseEventKind};
use crossterm::{execute, terminal::size};

use super::types::*;
use super::app::App;

impl App {
    pub(crate) fn handle_file_select_input(&mut self, key: KeyEvent) {
        match key.code {
            KeyCode::Char('q') | KeyCode::Esc => self.should_quit = true,
            KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => self.should_quit = true,
            KeyCode::F(2) => {
                self.mouse_mode = !self.mouse_mode;
                if self.mouse_mode {
                    execute!(std::io::stdout(), crossterm::event::EnableMouseCapture).ok();
                } else {
                    execute!(std::io::stdout(), crossterm::event::DisableMouseCapture).ok();
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
                                self.textarea = tui_textarea::TextArea::from(content.lines());
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

                                // Cache first platform immediately
                                self.cache_first_platform();
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

    pub(crate) fn handle_editor_input(&mut self, key: KeyEvent) {
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
                    execute!(std::io::stdout(), crossterm::event::EnableMouseCapture).ok();
                } else {
                    execute!(std::io::stdout(), crossterm::event::DisableMouseCapture).ok();
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
                KeyCode::Left => {
                    let current = self.platform_list_state.selected().unwrap_or(0);
                    if current > 0 {
                        // Select previous platform
                        let new_selection = current - 1;
                        self.select_platform(new_selection);
                        // Scroll left if selection is now out of view
                        if new_selection < self.platform_scroll_offset {
                            self.platform_scroll_offset = new_selection;
                        }
                        return;
                    } else {
                        // At beginning, scroll left if possible
                        if self.platform_scroll_offset > 0 {
                            self.platform_scroll_offset -= 1;
                            // Keep selection at 0, platform stays the same
                        }
                        return;
                    }
                }
                KeyCode::Right => {
                    let current = self.platform_list_state.selected().unwrap_or(0);
                    if current < self.platform_entries.len() - 1 {
                        // Select next platform
                        let new_selection = current + 1;
                        self.select_platform(new_selection);
                        // Scroll right if selection is now out of view
                        if new_selection >= self.platform_scroll_offset + super::types::MAX_VISIBLE_PLATFORMS {
                            self.platform_scroll_offset = new_selection - super::types::MAX_VISIBLE_PLATFORMS + 1;
                        }
                        return;
                    } else {
                        // At end, scroll right if possible
                        if self.platform_scroll_offset + super::types::MAX_VISIBLE_PLATFORMS < self.platform_entries.len() {
                            self.platform_scroll_offset += 1;
                            // Keep selection at last, platform stays the same
                        }
                        return;
                    }
                }
                KeyCode::PageUp => {
                    if self.url_scroll_offset > 0 {
                        self.url_scroll_offset = self.url_scroll_offset.saturating_sub(super::types::PAGE_SCROLL_AMOUNT);
                    }
                    return;
                }
                KeyCode::PageDown => {
                    let max_scroll = self.calculate_max_scroll_offset(self.url_viewer_height);
                    if self.url_scroll_offset < max_scroll {
                        // Scroll by roughly one screen height
                        let scroll_amount = self.url_viewer_height.saturating_sub(super::types::URL_VIEWER_MIN_HEIGHT).max(super::types::PAGE_SCROLL_AMOUNT);
                        self.url_scroll_offset = (self.url_scroll_offset + scroll_amount).min(max_scroll);
                    }
                    return;
                }
                KeyCode::Home => {
                    self.url_scroll_offset = 0;
                    return;
                }
                KeyCode::End => {
                    // Calculate URL viewer height dynamically
                    let url_viewer_height = match self.view_mode {
                        ViewMode::Both => {
                            // In Both mode, URL viewer takes remaining space after platforms bar
                            let editor_height = (super::types::DEFAULT_TERM_HEIGHT * super::types::EDITOR_HEIGHT_PERCENT / 100) as u16;
                            let platforms_bar_height: u16 = 3;
                            let help_height: u16 = 3;
                            super::types::DEFAULT_TERM_HEIGHT.saturating_sub(editor_height).saturating_sub(platforms_bar_height).saturating_sub(help_height)
                        }
                        ViewMode::PlatformsOnly => {
                            // In PlatformsOnly mode, URL viewer takes most of the space
                            let help_height: u16 = 3;
                            let platforms_height_estimate: u16 = super::types::PLATFORM_WIDTH_PERCENT as u16; // Use percentage as estimate
                            super::types::DEFAULT_TERM_HEIGHT.saturating_sub(help_height).saturating_sub(platforms_height_estimate)
                        }
                        ViewMode::EditorOnly => 0, // No URL viewer in editor-only mode
                    };

                    let max_scroll = self.calculate_max_scroll_offset(url_viewer_height);
                    self.url_scroll_offset = max_scroll;
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
                let input = tui_textarea::Input::from(key);
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

    pub(crate) fn handle_mouse_input(&mut self, mouse_event: MouseEvent) {
        if mouse_event.kind != MouseEventKind::Down(MouseButton::Left) {
            return;
        }

        let (term_width, term_height) = size().unwrap_or((80, 24));
        let area = ratatui::layout::Rect::new(0, 0, term_width, term_height);

        match self.state {
            AppState::FileSelect => {
                let chunks = ratatui::layout::Layout::default()
                    .direction(ratatui::layout::Direction::Vertical)
                    .constraints([
                        ratatui::layout::Constraint::Min(3),
                        ratatui::layout::Constraint::Max(94),
                        ratatui::layout::Constraint::Min(3)
                    ])
                    .split(area);
                let file_list_rect = chunks[1];

                if file_list_rect.contains(ratatui::layout::Position::new(mouse_event.column, mouse_event.row)) {
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
                                    self.textarea = tui_textarea::TextArea::from(content.lines());
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
                        let chunks = ratatui::layout::Layout::default()
                            .direction(ratatui::layout::Direction::Vertical)
                            .constraints([ratatui::layout::Constraint::Max(97), ratatui::layout::Constraint::Min(3)])
                            .split(area);
                        let content_chunks = ratatui::layout::Layout::default()
                            .direction(ratatui::layout::Direction::Horizontal)
                            .constraints([ratatui::layout::Constraint::Percentage(super::types::PLATFORM_WIDTH_PERCENT as u16), ratatui::layout::Constraint::Fill(1)])
                            .split(chunks[0]);
                        let platform_rect = content_chunks[0];

                        if platform_rect.contains(ratatui::layout::Position::new(mouse_event.column, mouse_event.row)) {
                            self.handle_platform_mouse_selection(&platform_rect, mouse_event);
                        }
                    }
                    ViewMode::Both => {
                        let chunks = ratatui::layout::Layout::default()
                            .direction(ratatui::layout::Direction::Vertical)
                            .constraints([ratatui::layout::Constraint::Max(50), ratatui::layout::Constraint::Max(50), ratatui::layout::Constraint::Min(3)])
                            .split(area);
                        let content_chunks = ratatui::layout::Layout::default()
                            .direction(ratatui::layout::Direction::Horizontal)
                            .constraints([ratatui::layout::Constraint::Percentage(super::types::PLATFORM_WIDTH_PERCENT as u16), ratatui::layout::Constraint::Fill(1)])
                            .split(chunks[1]);
                        let platform_rect = content_chunks[0];

                        if platform_rect.contains(ratatui::layout::Position::new(mouse_event.column, mouse_event.row)) {
                            self.handle_platform_mouse_selection(&platform_rect, mouse_event);
                        }
                    }
                }
            }
        }
    }

    fn handle_platform_mouse_selection(&mut self, platform_rect: &ratatui::layout::Rect, mouse_event: MouseEvent) {
        let item_index = (mouse_event.row as usize).saturating_sub(platform_rect.y as usize + 1);
        if item_index < self.platform_entries.len() {
            self.select_platform_with_cache(item_index, false);
        }
    }
}
