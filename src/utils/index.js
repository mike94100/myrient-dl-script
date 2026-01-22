/**
 * Utility functions for the ROM Collection Browser
 */

/**
 * Format bytes into human-readable format
 */
export function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Extract game name from filename for deduplication
 */
export function extractGameName(filename) {
  // Decode URL encoding first
  filename = decodeURIComponent(filename);

  // Remove extension and clean up filename for deduplication
  let name = filename.replace(/\.(zip|7z|rar)$/i, '');

  // Remove common ROM tags and version info
  name = name.replace(/\s*\([^)]*\)/g, ''); // Remove parentheses content
  name = name.replace(/\s*\[[^\]]*\]/g, ''); // Remove brackets content
  name = name.replace(/v\d+(\.\d+)?/gi, ''); // Remove version numbers
  name = name.replace(/rev\s*\d+/gi, ''); // Remove revision info
  name = name.replace(/\s+/g, ' ').trim(); // Normalize spaces

  return name.toLowerCase();
}

/**
 * Deduplicate files based on game name
 */
export function deduplicateFiles(files) {
  const seen = new Set();
  return files.filter((file) => {
    const gameName = extractGameName(file.url.split('/').pop());
    if (seen.has(gameName)) {
      return false;
    }
    seen.add(gameName);
    return true;
  });
}

/**
 * Download file as blob
 */
export function downloadFile(content, filename) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Group platforms by manufacturer
 */
export function groupPlatformsByManufacturer(platformMetadata) {
  const manufacturerGroups = {};
  const otherPlatforms = [];

  Object.keys(platformMetadata.platforms).forEach((platformKey) => {
    const platform = platformMetadata.platforms[platformKey];
    const manufacturer = platform.manufacturer || 'Other';

    if (!manufacturerGroups[manufacturer]) {
      manufacturerGroups[manufacturer] = [];
    }
    manufacturerGroups[manufacturer].push({
      key: platformKey,
      displayName: `${platform.manufacturer} - ${platform.console}`,
      platform: platform,
    });
  });

  return { manufacturerGroups, otherPlatforms };
}

/**
 * Create debounced function
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * DOM utility functions
 */
export const dom = {
  /**
   * Get element by ID with error handling
   */
  getElement(id) {
    const element = document.getElementById(id);
    if (!element) {
      console.error(`Element with id '${id}' not found`);
    }
    return element;
  },

  /**
   * Create element with attributes and content
   */
  createElement(tag, attributes = {}, content = '') {
    const element = document.createElement(tag);

    Object.keys(attributes).forEach((key) => {
      if (key === 'className') {
        element.className = attributes[key];
      } else if (key === 'textContent') {
        element.textContent = attributes[key];
      } else if (key === 'innerHTML') {
        element.innerHTML = attributes[key];
      } else {
        element.setAttribute(key, attributes[key]);
      }
    });

    if (content && !attributes.textContent && !attributes.innerHTML) {
      element.textContent = content;
    }

    return element;
  },

  /**
   * Add event listener with error handling
   */
  addEvent(element, event, handler) {
    if (!element) {
      console.error('Cannot add event listener to null element');
      return;
    }
    element.addEventListener(event, handler);
  },

  /**
   * Remove all children from element
   */
  clearElement(element) {
    if (!element) return;
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
  },
};
