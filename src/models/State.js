/**
 * Centralized state management for the ROM Collection Browser
 */
export class AppState {
  constructor() {
    this.reset();
  }

  reset() {
    this.platforms = {};
    this.selectedPlatforms = new Set();
    this.filters = {
      include: [],
      exclude: [],
      deduplication: true,
    };
    this.collections = {};
    this.currentTab = 'platforms';
    this.metadata = null;
    this.filtersData = null;
    this.initialized = false;
  }

  // Platform selection methods
  selectPlatform(platformKey) {
    this.selectedPlatforms.add(platformKey);
  }

  deselectPlatform(platformKey) {
    this.selectedPlatforms.delete(platformKey);
  }

  togglePlatform(platformKey) {
    if (this.selectedPlatforms.has(platformKey)) {
      this.deselectPlatform(platformKey);
    } else {
      this.selectPlatform(platformKey);
    }
  }

  clearPlatformSelection() {
    this.selectedPlatforms.clear();
  }

  getSelectedPlatforms() {
    return Array.from(this.selectedPlatforms);
  }

  // Filter methods
  updateFilter(type, value) {
    if (Array.isArray(this.filters[type])) {
      this.filters[type] = value;
    } else {
      this.filters[type] = value;
    }
  }

  getFilterTerms() {
    return { ...this.filters };
  }

  // Collection methods
  setCollection(platformKey, data) {
    this.collections[platformKey] = {
      ...data,
      filteredUrls: [],
    };
  }

  getCollection(platformKey) {
    return this.collections[platformKey];
  }

  getAllCollections() {
    return this.collections;
  }

  updateFilteredUrls(platformKey, urls) {
    if (this.collections[platformKey]) {
      this.collections[platformKey].filteredUrls = urls;
    }
  }

  // Metadata methods
  setMetadata(metadata) {
    this.metadata = metadata;
    this.initialized = true;
  }

  getMetadata() {
    return this.metadata;
  }

  // Filters data methods
  setFilters(filtersData) {
    this.filtersData = filtersData;
  }

  getFiltersData() {
    return this.filtersData;
  }

  // Utility methods
  isInitialized() {
    return this.initialized;
  }

  hasSelectedPlatforms() {
    return this.selectedPlatforms.size > 0;
  }

  getTotalStats() {
    const platforms = this.getSelectedPlatforms();
    let totalFiles = 0;
    let totalIncludedFiles = 0;
    let totalSize = 0;
    let totalIncludedSize = 0;

    platforms.forEach((platformKey) => {
      const collection = this.getCollection(platformKey);
      if (collection) {
        const allFiles = collection.files || [];
        const includedUrls = collection.filteredUrls || [];
        const includedFiles = allFiles.filter((f) => includedUrls.includes(f.url));

        totalFiles += allFiles.length;
        totalIncludedFiles += includedFiles.length;
        totalSize += allFiles.reduce((sum, file) => sum + (file.size || 0), 0);
        totalIncludedSize += includedFiles.reduce((sum, file) => sum + (file.size || 0), 0);
      }
    });

    return {
      platforms: platforms.length,
      totalFiles,
      totalIncludedFiles,
      totalSize,
      totalIncludedSize,
    };
  }
}
