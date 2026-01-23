import { AppState } from './models/State.js';
import { TabManager } from './components/TabManager.js';
import { PlatformSelector } from './components/PlatformSelector.js';
import { FilterManager } from './components/FilterManager.js';
import { ResultsDisplay } from './components/ResultsDisplay.js';
import * as utils from './utils/index.js';

/**
 * Main application class that coordinates all components
 */
export class App {
    constructor() {
        this.state = new AppState();
        this.utils = utils;

        // Initialize components
        this.tabManager = new TabManager(this);
        this.platformSelector = new PlatformSelector(this);
        this.filterManager = new FilterManager(this);
        this.resultsDisplay = new ResultsDisplay(this);
    }

    /**
     * Initialize the application
     */
    async init() {
        try {
            console.log('Initializing ROM Collection Browser...');

            // Load metadata and templates
            await this.loadResources();

            // Initialize components
            this.tabManager.init();
            this.platformSelector.init();
            this.filterManager.initializePresets();
            this.filterManager.bindEvents();
            this.resultsDisplay.init();

            // Setup import functionality
            this.setupImportHandler();

            console.log('ROM Collection Browser initialized successfully');
        } catch (error) {
            console.error('Failed to initialize application:', error);
        }
    }

    /**
     * Load configuration data
     */
    async loadResources() {
        const [metadataResp, filtersResp] = await Promise.all([
            fetch('config/metadata.json'),
            fetch('config/filters.json')
        ]);

        const metadata = await metadataResp.json();
        const filters = await filtersResp.json();

        // Update state
        this.state.setMetadata(metadata);
        this.state.setFilters(filters);
    }

    /**
     * Handle platform selection changes
     */
    handlePlatformSelection() {
        // This is handled by the PlatformSelector component
    }

    /**
     * Apply filters across all collections
     */
    applyFilters() {
        this.filterManager.applyFilters();
    }

    /**
     * Reset filters to defaults
     */
    resetFilters() {
        this.filterManager.resetFilters();
    }

    /**
     * Download Bash script
     */
    downloadBashScript() {
        this.resultsDisplay.downloadBashScript();
    }

    /**
     * Download Python script
     */
    downloadPythonScript() {
        this.resultsDisplay.downloadPythonScript();
    }

    /**
     * Toggle platform section visibility
     */
    togglePlatformSection(platform) {
        this.resultsDisplay.togglePlatformSection(platform);
    }

    /**
     * Toggle manufacturer section visibility
     */
    toggleManufacturerSection(manufacturer) {
        this.platformSelector.toggleManufacturerSection(manufacturer);
    }

    /**
     * Toggle file override
     */
    toggleFileOverride(fileUrl, platform) {
        this.resultsDisplay.toggleFileOverride(fileUrl, platform);
    }

    /**
     * Switch to a different tab
     */
    switchTab(tabName) {
        this.tabManager.switchTab(tabName);
    }

    /**
     * Import JSON collection data
     */
    importJson(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                this.loadImportedCollection(data);
            } catch (error) {
                alert('Invalid JSON file: ' + error.message);
            }
        };
        reader.readAsText(file);
    }

    /**
     * Setup import file handler
     */
    setupImportHandler() {
        const importInput = document.getElementById('json-import');
        if (importInput) {
            importInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    this.importJson(file);
                }
            });
        }
    }

    /**
     * Load imported collection data
     */
    loadImportedCollection(data) {
        if (!data.platforms) {
            alert('Invalid collection format: missing platforms');
            return;
        }

        // Clear current state
        this.state.clearPlatformSelection();
        this.state.collections = {};

        // Load collection data
        Object.keys(data.platforms).forEach(platformKey => {
            const platformData = data.platforms[platformKey];
            const urls = platformData.urls || [];

            // Create collection data
            const collection = {
                platform: platformKey,
                title: platformData.title || platformKey,
                description: data.description || '',
                files: urls.map(url => ({ url, name: url.split('/').pop(), size: 0 })),
                filteredUrls: urls
            };

            this.state.setCollection(platformKey, collection);
            this.state.selectPlatform(platformKey);
        });

        // Update UI
        this.resultsDisplay.displayCollections();
        this.switchTab('results');
    }
}

// Global functions for backward compatibility with HTML onclick handlers
let appInstance = null;

window.switchTab = function(tabName) {
    if (appInstance) {
        appInstance.switchTab(tabName);
    }
};

window.applyFilters = function() {
    if (appInstance) {
        appInstance.applyFilters();
    }
};

window.resetFilters = function() {
    if (appInstance) {
        appInstance.resetFilters();
    }
};

window.exportJson = function() {
    if (appInstance) {
        appInstance.resultsDisplay.exportJson();
    }
};

window.exportZip = function() {
    if (appInstance) {
        appInstance.resultsDisplay.exportZip();
    }
};

window.togglePlatformSection = function(platform) {
    if (appInstance) {
        appInstance.togglePlatformSection(platform);
    }
};

window.toggleManufacturerSection = function(manufacturer) {
    if (appInstance) {
        appInstance.toggleManufacturerSection(manufacturer);
    }
};

window.toggleFileOverride = function(fileUrl, platform) {
    if (appInstance) {
        appInstance.toggleFileOverride(fileUrl, platform);
    }
};

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    appInstance = new App();
    await appInstance.init();
});
