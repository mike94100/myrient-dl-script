import { dom } from '../utils/index.js';

/**
 * Manages tab switching functionality
 */
export class TabManager {
  constructor(app) {
    this.app = app;
    this.currentTab = 'platforms';
    this.filtersInitialized = false;
  }

  /**
   * Initialize tab event listeners
   */
  init() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach((button) => {
      dom.addEvent(button, 'click', (e) => {
        const tabName = e.target.getAttribute('onclick')?.match(/switchTab\('([^']+)'\)/)?.[1];
        if (tabName) {
          this.switchTab(tabName);
        }
      });
    });
  }

  /**
   * Switch to a specific tab
   */
  switchTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach((content) => content.classList.remove('active'));

    // Remove active class from all tab buttons
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach((btn) => btn.classList.remove('active'));

    // Show the selected tab content and activate the button
    const selectedTab = document.getElementById(`${tabName}-tab`);
    const selectedBtn = document.querySelector(`.tab-btn[onclick="switchTab('${tabName}')"]`);

    if (selectedTab && selectedBtn) {
      selectedTab.classList.add('active');
      selectedBtn.classList.add('active');
      this.currentTab = tabName;

      // Initialize filters when switching to filters tab
      if (tabName === 'filters') {
        this.initializeFiltersIfNeeded();
      }

      // If switching to results tab and we have selected platforms, ensure results are displayed
      if (tabName === 'results' && this.app.state.hasSelectedPlatforms()) {
        this.app.resultsDisplay.displayCollections();
      }

      // Update app state
      this.app.state.currentTab = tabName;
    }
  }

  /**
   * Initialize filters when first accessing the filters tab
   */
  initializeFiltersIfNeeded() {
    if (!this.filtersInitialized) {
      // Initialize filter fields with default values
      this.app.filterManager.initializeFilterFields(
        'include-filters-container',
        this.app.state.filters.include
      );
      this.app.filterManager.initializeFilterFields(
        'exclude-filters-container',
        this.app.state.filters.exclude
      );

      this.filtersInitialized = true;
    }
  }

  /**
   * Show or hide the results tab
   */
  setResultsTabVisible(visible) {
    const resultsTabBtn = document.getElementById('results-tab-btn');
    if (resultsTabBtn) {
      resultsTabBtn.style.display = visible ? 'inline-block' : 'none';
    }
  }

  /**
   * Get current active tab
   */
  getCurrentTab() {
    return this.currentTab;
  }
}
