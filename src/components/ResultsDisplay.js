import { dom, formatBytes } from '../utils/index.js';
import JSZip from 'jszip';

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
   * Generate export data for selected platforms
   */
  generateExportData() {
    const platforms = this.app.state.getSelectedPlatforms();
    if (platforms.length === 0) {
      alert('No platforms selected');
      return null;
    }

    // Build export data
    const exportData = {
      title: '',
      description: '',
      platforms: {}
    };

    // Set title and description
    if (platforms.length === 1) {
      const platform = platforms[0];
      const collection = this.app.state.getCollection(platform);
      if (collection) {
        exportData.title = collection.title;
        exportData.description = collection.description;
      } else {
        exportData.title = `${platform} ROM Collection`;
      }
    } else {
      exportData.title = `Multi-Platform ROM Collection (${platforms.length} platforms)`;
      exportData.description = platforms
        .map((p) => {
          const metadata = this.app.state.metadata?.platforms[p];
          return metadata ? `${metadata.manufacturer} - ${metadata.console}` : p;
        })
        .join(', ');
    }

    // Add platform data
    let totalUrls = 0;
    platforms.forEach((platformKey) => {
      const collection = this.app.state.getCollection(platformKey);
      const metadata = this.app.state.metadata?.platforms[platformKey];

      if (collection && collection.filteredUrls && collection.filteredUrls.length > 0) {
        exportData.platforms[platformKey] = {
          title: collection.title,
          directory: metadata?.download_directory || platformKey,
          urls: collection.filteredUrls
        };
        totalUrls += collection.filteredUrls.length;
      }
    });

    if (totalUrls === 0) {
      alert('No files to export');
      return null;
    }

    return exportData;
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
   * Export collection as JSON
   */
  exportJson() {
    const exportData = this.generateExportData();
    if (!exportData) return;

    const jsonContent = JSON.stringify(exportData, null, 2);
    const filename = exportData.title.toLowerCase().replace(/[^a-z0-9]+/g, '_') + '.json';

    const { downloadFile } = this.app.utils;
    downloadFile(jsonContent, filename);
  }

  /**
   * Export ZIP containing JSON and scripts
   */
  exportZip() {
    const exportData = this.generateExportData();
    if (!exportData) return;

    // Create ZIP with JSON and scripts
    this.createScriptsZip(exportData, true);
  }

  /**
   * Create ZIP file with scripts and optionally JSON
   */
  async createScriptsZip(exportData, includeJson) {
    const baseName = exportData.title.toLowerCase().replace(/[^a-z0-9]+/g, '_');

    try {
      const zip = new JSZip();

      // Fetch and add scripts
      const [bashResponse, pythonResponse] = await Promise.all([
        fetch('bin/download.sh'),
        fetch('bin/download.py')
      ]);

      const bashScript = await bashResponse.text();
      const pythonScript = await pythonResponse.text();

      zip.file(`${baseName}_download.sh`, bashScript);
      zip.file(`${baseName}_download.py`, pythonScript);

      if (includeJson) {
        const jsonContent = JSON.stringify(exportData, null, 2);
        zip.file(`${baseName}.json`, jsonContent);
      }

      // Generate ZIP file
      const zipBlob = await zip.generateAsync({ type: 'blob' });

      // Download the ZIP file
      const { downloadFile } = this.app.utils;
      downloadFile(zipBlob, `${baseName}_package.zip`, 'application/zip');
    } catch (error) {
      console.error('Failed to create ZIP:', error);
      alert('Failed to create ZIP file');
    }
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
