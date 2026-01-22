import { dom, formatBytes } from '../utils/index.js';

/**
 * Handles results display UI and logic
 */
export class ResultsDisplay {
  constructor(app) {
    this.app = app;
    this.collectionInfo = null;
  }

  /**
   * Initialize the results display
   */
  init() {
    this.collectionInfo = dom.getElement('collection-info');
  }

  /**
   * Display collections for selected platforms
   */
  displayCollections() {
    const platforms = this.app.state.getSelectedPlatforms();
    if (platforms.length === 0) return;

    const titleElement = dom.getElement('collection-title');
    const descElement = dom.getElement('collection-description');

    if (!titleElement || !descElement) {
      console.error('Collection title or description elements not found');
      return;
    }

    // Update title and description for multiple platforms
    if (platforms.length === 1) {
      const platform = platforms[0];
      const collection = this.app.state.getCollection(platform);
      if (collection) {
        titleElement.textContent = collection.title;
        descElement.textContent = collection.description;
      } else {
        titleElement.textContent = 'No collection data found';
        descElement.textContent = `Failed to load data for ${platform}`;
      }
    } else {
      titleElement.textContent = `Multiple Platforms ROM Collection (${platforms.length} platforms)`;
      descElement.textContent = platforms
        .map((p) => {
          const metadata = this.app.state.metadata?.platforms[p];
          return metadata ? `${metadata.manufacturer} - ${metadata.console}` : p;
        })
        .join(', ');
    }

    // Update total stats
    this.updateTotalStats();

    // Display platform sections
    this.displayPlatformSections();
  }

  /**
   * Update total statistics display
   */
  updateTotalStats() {
    const stats = this.app.state.getTotalStats();
    const statsText = `${stats.platforms} platforms, ${stats.totalFiles} total files (${formatBytes(stats.totalSize)}), ${stats.totalIncludedFiles} included (${formatBytes(stats.totalIncludedSize)})`;

    const statsElement = dom.getElement('total-stats-text');
    if (statsElement) {
      statsElement.textContent = statsText;
    }
  }

  /**
   * Display individual platform sections
   */
  displayPlatformSections() {
    const platformSections = dom.getElement('platform-sections');
    if (!platformSections) return;

    dom.clearElement(platformSections);

    const platforms = this.app.state.getSelectedPlatforms();

    // Create section for each platform
    platforms.forEach((platformKey, index) => {
      const collection = this.app.state.getCollection(platformKey);
      if (!collection) return;

      const allFiles = collection.files || [];
      const includedUrls = collection.filteredUrls || [];
      const includedFiles = allFiles.filter((f) => includedUrls.includes(f.url));
      const excludedFiles = allFiles.filter((f) => !includedUrls.includes(f.url));

      const section = this.createPlatformSection(collection, includedFiles, excludedFiles, index);
      platformSections.appendChild(section);
    });
  }

  /**
   * Create a platform section element
   */
  createPlatformSection(collection, includedFiles, excludedFiles, index) {
    const section = dom.createElement('div', { className: 'platform-section' });

    const allFiles = collection.files || [];
    const totalSize = allFiles.reduce((sum, file) => sum + (file.size || 0), 0);
    const includedSize = includedFiles.reduce((sum, file) => sum + (file.size || 0), 0);

    // Use unique IDs with index to avoid conflicts
    const includedId = `included-${collection.platform}-${index}`;
    const excludedId = `excluded-${collection.platform}-${index}`;

    section.innerHTML = `
            <h3>${collection.title} <button class="toggle-btn" onclick="togglePlatformSection('${collection.platform}', ${index})">&minus;</button></h3>
            <div class="stats">
                ${allFiles.length} files (${formatBytes(totalSize)}),
                ${includedFiles.length} included (${formatBytes(includedSize)}),
                ${excludedFiles.length} excluded
            </div>
            <div class="platform-content">
                <div class="file-container">
                    <div class="file-section">
                        <h4>Included Files (${includedFiles.length})</h4>
                        <div class="file-list" id="${includedId}"></div>
                    </div>
                    <div class="file-section">
                        <h4>Excluded Files (${excludedFiles.length})</h4>
                        <div class="file-list" id="${excludedId}"></div>
                    </div>
                </div>
            </div>
        `;

    // Populate file lists directly using the elements we just created
    const includedList = section.querySelector(`#${includedId}`);
    const excludedList = section.querySelector(`#${excludedId}`);

    if (includedList) {
      this.populateFileListDirect(includedList, includedFiles, collection.platform, true);
    }
    if (excludedList) {
      this.populateFileListDirect(excludedList, excludedFiles, collection.platform, false);
    }

    return section;
  }

  /**
   * Populate a file list with items using a DOM element directly
   */
  populateFileListDirect(listElement, files, platformKey, isIncluded) {
    if (!listElement) return;

    dom.clearElement(listElement);

    files.forEach((file) => {
      const filename = decodeURIComponent(file.url.split('/').pop()).replace(
        /\.(zip|7z|rar)$/i,
        ''
      );
      const classes = isIncluded ? 'file-item included' : 'file-item excluded';

      const item = dom.createElement('div', {
        className: classes,
        textContent: filename,
        onclick: `toggleFileOverride('${file.url}', '${platformKey}')`,
      });

      listElement.appendChild(item);
    });
  }

  /**
   * Toggle platform section visibility
   */
  togglePlatformSection(platform, index) {
    // Find the section by looking for the button with the matching onclick
    const buttons = document.querySelectorAll('.toggle-btn');
    let targetSection = null;

    buttons.forEach(button => {
      if (button.getAttribute('onclick') === `togglePlatformSection('${platform}', ${index})`) {
        targetSection = button.closest('.platform-section');
      }
    });

    if (!targetSection) return;

    const content = targetSection.querySelector('.platform-content');
    const toggleBtn = targetSection.querySelector('.toggle-btn');

    if (content.style.display === 'none') {
      content.style.display = 'block';
      toggleBtn.innerHTML = '&minus;';
    } else {
      content.style.display = 'none';
      toggleBtn.textContent = '+';
    }
  }

  /**
   * Toggle file override (include/exclude manually)
   */
  toggleFileOverride(fileUrl, platform) {
    const state = this.app.state.getCollection(platform);
    if (!state) return;

    // For now, we'll need to implement manual overrides per platform
    // This would require extending the state to track manual overrides per platform
    console.log('Toggle file override:', fileUrl, platform);

    // TODO: Implement manual file override functionality
    // This would involve updating filtered URLs and re-displaying
  }

  /**
   * Download scripts for selected platforms
   */
  downloadBashScript() {
    const platforms = this.app.state.getSelectedPlatforms();
    if (platforms.length === 0 || !this.app.state.templates.bash) {
      alert('No data loaded or template not loaded');
      return;
    }

    // Collect all URLs from all platforms
    let allUrls = [];
    platforms.forEach((platform) => {
      const collection = this.app.state.getCollection(platform);
      if (collection) {
        allUrls = allUrls.concat(collection.filteredUrls || []);
      }
    });

    if (allUrls.length === 0) {
      alert('No files to download');
      return;
    }

    const platformsList = platforms
      .map((p) => {
        const metadata = this.app.state.metadata?.platforms[p];
        return metadata ? `${metadata.manufacturer} - ${metadata.console}` : p;
      })
      .join(', ');

    // Generate download script
    this.generateDownloadScript('bash', allUrls, platforms, platformsList);
  }

  downloadPythonScript() {
    const platforms = this.app.state.getSelectedPlatforms();
    if (platforms.length === 0 || !this.app.state.templates.python) {
      alert('No data loaded or template not loaded');
      return;
    }

    // Collect all URLs from all platforms
    let allUrls = [];
    platforms.forEach((platform) => {
      const collection = this.app.state.getCollection(platform);
      if (collection) {
        allUrls = allUrls.concat(collection.filteredUrls || []);
      }
    });

    if (allUrls.length === 0) {
      alert('No files to download');
      return;
    }

    const platformsList = platforms
      .map((p) => {
        const metadata = this.app.state.metadata?.platforms[p];
        return metadata ? `${metadata.manufacturer} - ${metadata.console}` : p;
      })
      .join(', ');

    // Generate download script
    this.generateDownloadScript('python', allUrls, platforms, platformsList);
  }

  /**
   * Generate and download script
   */
  generateDownloadScript(type, allUrls, platforms, platformsList) {
    // This would use the template system - for now just show a placeholder
    const scriptContent = `# Auto-generated ${type} download script for ${platformsList}\n# ${allUrls.length} files total\n\nprint("Download script generated!")`;

    const filename =
      platforms.length === 1
        ? `${platforms[0]}_download.${type === 'bash' ? 'sh' : 'py'}`
        : `multi_platform_download.${type === 'bash' ? 'sh' : 'py'}`;

    // Download the file
    const { downloadFile } = this.app.utils;
    downloadFile(scriptContent, filename);
  }

  /**
   * Show the results display
   */
  show() {
    if (this.collectionInfo) {
      this.collectionInfo.style.display = 'block';
    }
  }

  /**
   * Hide the results display
   */
  hide() {
    if (this.collectionInfo) {
      this.collectionInfo.style.display = 'none';
    }
  }
}
