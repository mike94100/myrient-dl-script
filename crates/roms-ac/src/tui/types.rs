//! # TUI Types Module
//!
//! Core data structures and type definitions for the Terminal User Interface.
//! This module defines the state management types, UI layout enums, and
//! configuration constants used throughout the TUI system.

use std::path::PathBuf;

/// Represents the current application state in the TUI.
///
/// The application can be in one of two primary modes:
/// - File selection mode for browsing and opening collection files
/// - Editor mode for viewing and editing collection configurations
#[derive(Clone, PartialEq)]
pub enum AppState {
    /// File browser mode - user can navigate directories and select TOML files
    FileSelect,
    /// Editor mode - user can view platforms, edit filters, and manage collections
    Editor,
}

/// Defines the current view layout of the TUI interface.
///
/// The TUI can display different combinations of the editor pane,
/// platform selector, and URL viewer to optimize the workflow.
#[derive(Clone, PartialEq)]
pub enum ViewMode {
    /// Show only the collection editor (full-screen editing)
    EditorOnly,
    /// Show only platforms and URL viewer (analysis mode)
    PlatformsOnly,
    /// Show all three panes: editor, platforms, and URL viewer
    Both,
}

/// Help context for displaying appropriate keybindings.
///
/// Different parts of the interface show different help text
/// to guide users through available actions.
#[derive(Clone, PartialEq)]
pub(crate) enum HelpType {
    /// Help for file selection and navigation
    Editor,
    /// Help for file browser operations
    FileBrowser,
}

/// Layout configuration for single-panel display modes.
///
/// Determines which content to show when only one panel is active.
#[derive(Clone, PartialEq)]
pub(crate) enum PanelType {
    /// Display collection editor only
    EditorOnly,
    /// Display platforms and URL viewer
    PlatformsOnly,
}

/// Current input focus within the TUI.
///
/// Determines which part of the interface receives keyboard input
/// and which UI elements are highlighted.
#[derive(Clone, PartialEq)]
pub enum Focus {
    /// Focus on platform selection and URL viewing
    Platforms,
    /// Focus on collection editor
    Editor,
}

/// File editing status for change tracking.
///
/// Tracks whether the current file has unsaved changes
/// and provides visual feedback to the user.
#[derive(Clone)]
pub enum FileStatus {
    /// File matches original content (no changes)
    Unchanged,
    /// File has unsaved edits
    PendingEdits,
    /// File was recently saved
    Saved,
}

/// Represents a file system entry in the file browser.
///
/// Contains metadata about files and directories shown in the
/// file selection interface.
#[derive(Clone)]
pub struct FileEntry {
    /// Full path to the file or directory
    pub path: PathBuf,
    /// Whether this entry is a directory
    pub is_dir: bool,
    /// Display name (filename or "dirname/")
    pub name: String,
}

// UI Constants
/// Maximum number of platforms to show before requiring scrolling.
/// This affects the horizontal platform bar layout.
pub const MAX_VISIBLE_PLATFORMS: usize = 3;

/// Percentage of terminal height allocated to the editor pane.
/// Used for calculating layout proportions in split-view modes.
pub const EDITOR_HEIGHT_PERCENT: u16 = 50;

/// Percentage of terminal width allocated to the platform selector.
/// Determines the horizontal split between platform list and URL viewer.
pub const PLATFORM_WIDTH_PERCENT: u16 = 15;

/// Default terminal height assumption for layout calculations.
/// Used when actual terminal size cannot be determined.
pub const DEFAULT_TERM_HEIGHT: u16 = 24;

/// Number of lines to scroll when using Page Up/Down keys.
/// Controls the scroll speed in the URL viewer.
pub const PAGE_SCROLL_AMOUNT: u16 = 10;

/// Minimum height reserved for the URL viewer content area.
/// Prevents the viewer from becoming unusable on small terminals.
pub const URL_VIEWER_MIN_HEIGHT: u16 = 2;

/// Indentation level for wrapped text lines in the URL viewer.
/// Improves readability of long URLs and descriptions.
pub const TEXT_WRAP_INDENT: usize = 2;
