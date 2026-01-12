use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Style},
    widgets::{Borders, List, ListItem, Paragraph, Wrap, Block},
    Frame,
};

use super::types::*;
use super::app::App;

impl App {
    pub(crate) fn ui(&mut self, f: &mut Frame) {
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

    fn layout_single_panel(&self, area: Rect) -> (Rect, Rect) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Max(97), Constraint::Min(3)])
            .split(area);
        (chunks[0], chunks[1])
    }

    fn draw_single_panel(&mut self, f: &mut Frame, area: Rect, panel_type: PanelType) {
        let (main_area, help_area) = self.layout_single_panel(area);

        match panel_type {
            PanelType::EditorOnly => {
                self.draw_collection_editor(f, main_area);
            }
            PanelType::PlatformsOnly => {
                // Platforms horizontal bar (3 lines) + URLs (remaining space)
                let content_chunks = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([Constraint::Length(3), Constraint::Fill(1)])
                    .split(main_area);
                self.draw_platform_selector_horizontal(f, content_chunks[0]);
                self.draw_url_viewer(f, content_chunks[1]);
            }
        }

        self.draw_help(f, help_area, HelpType::Editor);
    }

    fn draw_editor(&mut self, f: &mut Frame) {
        let area = f.area();

        match self.view_mode {
            ViewMode::EditorOnly => {
                self.draw_single_panel(f, area, PanelType::EditorOnly);
            }
            ViewMode::PlatformsOnly => {
                self.draw_single_panel(f, area, PanelType::PlatformsOnly);
            }
            ViewMode::Both => {
                // Both: editor + platforms + URL viewer + help
                let editor_height = (DEFAULT_TERM_HEIGHT * EDITOR_HEIGHT_PERCENT / 100) as u16;
                let chunks = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([Constraint::Max(editor_height), Constraint::Max(editor_height), Constraint::Min(3)])
                    .split(area);

                self.draw_collection_editor(f, chunks[0]);

                // Platforms bar (3 lines) + URL viewer (remaining)
                let content_chunks = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([Constraint::Length(3), Constraint::Fill(1)])
                    .split(chunks[1]);

                self.draw_platform_selector_horizontal(f, content_chunks[0]);
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

    fn draw_platform_selector_horizontal(&self, f: &mut Frame, area: Rect) {
        let border_color = match self.focus {
            Focus::Editor => Color::White,
            Focus::Platforms => Color::Cyan,
        };

        let available_width = area.width as usize;
        let mut display_text = String::new();

        // Add left scroll indicator if there are platforms before scroll offset
        if self.platform_scroll_offset > 0 {
            display_text.push('<');
        }

        // Show platforms starting from scroll offset, fitting as many as possible
        let mut current_width = display_text.len();
        let mut visible_count = 0;

        for (i, platform) in self.platform_entries.iter().enumerate().skip(self.platform_scroll_offset) {
            let separator = if visible_count > 0 { " | " } else { "" };
            let platform_display = if Some(i) == self.platform_list_state.selected() {
                format!("[{}]", platform)
            } else {
                platform.clone()
            };

            let item_text = format!("{}{}", separator, platform_display);
            let item_width = item_text.len();

            // Check if this item would fit
            if current_width + item_width > available_width.saturating_sub(1) { // Leave room for right indicator
                break;
            }

            display_text.push_str(&item_text);
            current_width += item_width;
            visible_count += 1;
        }

        // Add right scroll indicator if there are more platforms after visible ones
        if self.platform_scroll_offset + visible_count < self.platform_entries.len() {
            if current_width + 1 <= available_width {
                display_text.push('>');
            }
        }

        let paragraph = Paragraph::new(display_text)
            .block(Block::default()
                .title("Platforms")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color)))
            .wrap(Wrap { trim: false });

        f.render_widget(paragraph, area);
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
            let wrapped_lines = Self::wrap_text_with_indent(line, inner_width, TEXT_WRAP_INDENT);
            for wrapped_line in wrapped_lines {
                content.push(ratatui::text::Line::from(vec![ratatui::text::Span::raw(wrapped_line)]));
            }
        }

        let paragraph = Paragraph::new(content)
            .block(block)
            .scroll((self.url_scroll_offset, 0));

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
            HelpType::Editor => match self.focus {
                Focus::Platforms => vec![
                    ratatui::text::Line::from(vec![
                        ratatui::text::Span::styled("←→", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" platforms/scroll, ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled("PgUp/PgDn", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" URLs, ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled("Tab", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" focus", Style::default().fg(Color::White)),
                    ]),
                    ratatui::text::Line::from(vec![
                        ratatui::text::Span::styled("Home/End", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" top/bottom, ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled("Ctrl+R", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" refresh, ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled("F2", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" mouse", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled(" | ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled(mouse_mode_str, Style::default().fg(Color::Cyan)),
                        ratatui::text::Span::styled(", ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled("F3", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" view", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled(" | ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled(view_mode_str, Style::default().fg(Color::Magenta)),
                    ]),
                    ratatui::text::Line::from(vec![
                        ratatui::text::Span::styled("Ctrl+S", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" save, ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled("Esc", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" back", Style::default().fg(Color::White)),
                    ]),
                ],
                Focus::Editor => vec![
                    ratatui::text::Line::from(vec![
                        ratatui::text::Span::styled("Esc", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" back, ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled("F2", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" toggle mouse", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled(" | ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled(mouse_mode_str, Style::default().fg(Color::Cyan)),
                        ratatui::text::Span::styled(", ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled("F3", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" toggle view", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled(" | ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled(view_mode_str, Style::default().fg(Color::Magenta)),
                        ratatui::text::Span::styled(", ", Style::default().fg(Color::White)),
                        ratatui::text::Span::styled("Ctrl+S", Style::default().fg(Color::Yellow)),
                        ratatui::text::Span::styled(" save", Style::default().fg(Color::White)),
                    ]),
                ],
            },
            HelpType::FileBrowser => vec![
                ratatui::text::Line::from(vec![
                    ratatui::text::Span::styled("↑↓", Style::default().fg(Color::Yellow)),
                    ratatui::text::Span::styled(" navigate, ", Style::default().fg(Color::White)),
                    ratatui::text::Span::styled("→/Enter", Style::default().fg(Color::Yellow)),
                    ratatui::text::Span::styled(" enter dir/select file, ", Style::default().fg(Color::White)),
                    ratatui::text::Span::styled("←", Style::default().fg(Color::Yellow)),
                    ratatui::text::Span::styled(" go up, ", Style::default().fg(Color::White)),
                    ratatui::text::Span::styled("Esc/q", Style::default().fg(Color::Yellow)),
                    ratatui::text::Span::styled(" quit", Style::default().fg(Color::White)),
                ]),
            ],
        };

        let paragraph = Paragraph::new(help_text)
            .style(Style::default().fg(Color::White))
            .block(Block::default().borders(Borders::ALL));

        f.render_widget(paragraph, area);
    }


}
