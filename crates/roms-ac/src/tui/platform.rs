
//! # TUI Platform Module
//!
//! Platform management and URL processing functionality for the TUI.
//! This module handles platform selection, URL caching, filtering, and display
//! formatting for the ROM collection management interface.

use super::app::App;

use log;

impl App {
    pub(crate) fn update_url_content_for_platform(&mut self) {
        log::debug!("Updating URL content for platform: {}", self.selected_platform);

        // Check cache validity first
        let current_hash = self.hash_toml_content();
        if self.cache_toml_hash != current_hash {
            log::info!("TOML content changed, clearing URL cache");
            self.url_cache.clear();
            self.cache_toml_hash = current_hash;
        }

        // Check if we have cached content for this platform
        if let Some(cached_urls) = self.url_cache.get(&self.selected_platform) {
            log::debug!("Using cached URL content for platform: {} ({} URLs)", self.selected_platform, cached_urls.len());
            self.url_content = cached_urls.clone();
            return;
        }

        log::debug!("No cached content found for platform: {}, loading from file", self.selected_platform);

        // Process URLs and cache them
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

                        // Convert to display format and cache
                        let display_urls: Vec<String> = filtered_urls.into_iter().map(|url| {
                            let filename = Self::extract_filename_from_url(&url);
                            if url.starts_with('#') {
                                format!("✗ {}", filename)
                            } else {
                                format!("✓ {}", filename)
                            }
                        }).collect();

                        // Cache the result
                        self.url_cache.insert(self.selected_platform.clone(), display_urls.clone());
                        self.url_content = display_urls;
                    } else {
                        // Fallback if TOML parsing fails - show all as included
                        let urls: Vec<String> = content.lines()
                            .filter(|line| !line.trim().is_empty())
                            .map(|line| line.to_string())
                            .collect();

                        let display_urls: Vec<String> = urls.into_iter().map(|url| {
                            let filename = Self::extract_filename_from_url(&url);
                            format!("✓ {}", filename)
                        }).collect();

                        // Cache the fallback result
                        self.url_cache.insert(self.selected_platform.clone(), display_urls.clone());
                        self.url_content = display_urls;
                    }
                }
            }
        }
    }

    pub(crate) fn refresh_filtering_preview(&mut self) {
        log::info!("Refreshing filtering preview for all platforms");

        if let Some(selected_file) = &self.selected_file {
            // Parse current editor content as TOML
            let toml_content = self.textarea.lines().join("\n");
            let filter = match crate::filters::CollectionFilter::new_from_content(&toml_content) {
                Ok(f) => {
                    log::debug!("Successfully parsed TOML filters");
                    f
                },
                Err(e) => {
                    log::error!("Failed to parse TOML content: {}", e);
                    self.save_message = Some("Invalid TOML!".to_string());
                    return;
                }
            };

            // Clear existing displays
            self.platform_url_displays.clear();

            // Process each platform sequentially (file I/O is fast enough)
            let selected_file_path = selected_file.to_string_lossy().to_string();

            for platform in &self.platform_entries {
                log::debug!("Processing platform: {} for filtering preview", platform);
                if let Ok((_, urls)) = Self::filter_platform_urls(&selected_file_path, platform.clone(), &filter) {
                    self.platform_url_displays.insert(platform.clone(), urls);
                } else {
                    log::warn!("Failed to filter URLs for platform: {}", platform);
                }
            }

            // Update the filtered preview mode
            self.filtered_preview_mode = true;
            log::info!("Filtering preview updated for {} platforms", self.platform_entries.len());

            // Update current display for selected platform
            self.update_current_url_display();
        } else {
            log::warn!("No selected file available for filtering preview");
        }
    }

    fn filter_platform_urls(collection_path: &str, platform: String, filter: &crate::filters::CollectionFilter) -> anyhow::Result<(String, Vec<String>)> {
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
        let display_urls = filtered_urls.into_iter().map(|url| {
            let filename = Self::extract_filename_from_url(&url);
            if url.starts_with('#') {
                format!("✗ {}", filename)
            } else {
                format!("✓ {}", filename)
            }
        }).collect();

        Ok((platform, display_urls))
    }

    pub(crate) fn update_current_url_display(&mut self) {
        if let Some(urls) = self.platform_url_displays.get(&self.selected_platform) {
            self.url_content = urls.clone();
        } else {
            self.url_content = Vec::new();
        }
    }

    pub(crate) fn save_all_url_lists(&mut self) {
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

    pub(crate) fn calculate_max_scroll_offset(&self, viewer_height: u16) -> u16 {
        let mut total_lines = 0u16;
        let inner_width = 80u16.saturating_sub(2) as usize; // Approximate width minus borders

        for line in &self.url_content {
            let wrapped_lines = Self::wrap_text_with_indent(line, inner_width, super::types::TEXT_WRAP_INDENT);
            total_lines = total_lines.saturating_add(wrapped_lines.len() as u16);
        }

        // Allow scrolling if content is taller than viewer
        if total_lines > viewer_height {
            total_lines.saturating_sub(viewer_height)
        } else {
            0
        }
    }

    pub(crate) fn wrap_text_with_indent(text: &str, width: usize, indent: usize) -> Vec<String> {
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
}
