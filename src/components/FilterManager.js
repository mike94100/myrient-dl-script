import { dom, deduplicateFiles } from '../utils/index.js';

/**
 * Handles filtering UI and logic
 */
export class FilterManager {
  constructor(app) {
    this.app = app;
    this.debouncedApplyFilters = this.app.utils.debounce(() => this.applyFilters(), 300);
  }

  /**
   * Apply filters to all collections
   */
  applyFilters() {
    const filterTerms = this.app.state.getFilterTerms();
    const collections = this.app.state.getAllCollections();

    // Apply filters to each platform separately
    Object.keys(collections).forEach((platformKey) => {
      const collection = collections[platformKey];
      const allFiles = collection.files;

      // Apply include/exclude filters first
      let filteredFiles = allFiles.filter((file) => {
        const filename = decodeURIComponent(file.url.split('/').pop()).toLowerCase();

        // Check exclude patterns
        if (filterTerms.exclude?.some((pattern) => filename.includes(pattern.toLowerCase()))) {
          return false;
        }

        // Check include patterns - if include terms exist, filename must contain at least one
        if (filterTerms.include && filterTerms.include.length > 0) {
          return filterTerms.include.some((term) => filename.includes(term.toLowerCase()));
        }

        return true;
      });

      // Apply deduplication if enabled
      if (filterTerms.deduplication) {
        filteredFiles = deduplicateFiles(filteredFiles);
      }

      // Store filtered URLs for this platform
      this.app.state.updateFilteredUrls(
        platformKey,
        filteredFiles.map((f) => f.url)
      );
    });

    // Update results display if collections are loaded
    if (this.app.state.hasSelectedPlatforms()) {
      this.app.resultsDisplay.displayCollections();
    }
  }

  /**
   * Reset filters to defaults
   */
  resetFilters() {
    // Reset filter fields to default values
    this.initializeFilterFields('include-filters-container', this.app.state.filters.include);
    this.initializeFilterFields('exclude-filters-container', this.app.state.filters.exclude);

    // Reset checkbox
    const dedupCheckbox = document.getElementById('deduplicate');
    if (dedupCheckbox) {
      dedupCheckbox.checked = true;
    }

    this.app.state.updateFilter('deduplication', true);

    this.applyFilters();
  }

  /**
   * Initialize filter field containers with terms
   */
  initializeFilterFields(containerId, initialTerms) {
    const container = dom.getElement(containerId);
    if (!container) return;

    dom.clearElement(container);

    if (initialTerms && initialTerms.length > 0) {
      initialTerms.forEach((term) => this.createFilterField(containerId, term));
    }

    // Always add one empty field at the end
    this.createFilterField(containerId);
  }

  /**
   * Create a filter field
   */
  createFilterField(containerId, initialValue = '') {
    const container = dom.getElement(containerId);
    if (!container) return null;

    const fieldRow = dom.createElement('div', { className: 'filter-field-row' });

    const input = dom.createElement('input', {
      type: 'text',
      value: initialValue,
      placeholder: 'Enter filter term...',
    });

    const deleteBtn = dom.createElement('button', {
      innerHTML: '&times;',
      title: 'Remove filter',
    });

    // Event listeners
    dom.addEvent(input, 'input', () => this.handleFilterInput(containerId));
    dom.addEvent(input, 'keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        this.handleFilterInput(containerId);
      }
    });
    dom.addEvent(deleteBtn, 'click', () => this.removeFilterField(fieldRow, containerId));

    fieldRow.appendChild(input);
    fieldRow.appendChild(deleteBtn);
    container.appendChild(fieldRow);

    return fieldRow;
  }

  /**
   * Remove a filter field
   */
  removeFilterField(fieldRow, containerId) {
    const container = dom.getElement(containerId);
    if (!container) return;

    container.removeChild(fieldRow);
    this.cleanupEmptyFields(containerId);
    this.debouncedApplyFilters();
  }

  /**
   * Handle filter input changes
   */
  handleFilterInput(containerId) {
    const container = dom.getElement(containerId);
    if (!container) return;

    const inputs = container.querySelectorAll('input');
    const lastInput = inputs[inputs.length - 1];

    // If the last field has content and it's not empty, add a new empty field
    if (lastInput && lastInput.value.trim() !== '') {
      this.createFilterField(containerId);
    }

    // Clean up empty fields (but keep at least one)
    this.cleanupEmptyFields(containerId);

    // Update state and apply filters
    this.updateFilterState(containerId);
    this.debouncedApplyFilters();
  }

  /**
   * Clean up empty filter fields
   */
  cleanupEmptyFields(containerId) {
    const container = dom.getElement(containerId);
    if (!container) return;

    const fieldRows = container.querySelectorAll('.filter-field-row');
    const inputs = Array.from(fieldRows).map((row) => row.querySelector('input'));

    // Remove empty fields except the last one
    for (let i = inputs.length - 2; i >= 0; i--) {
      if (inputs[i].value.trim() === '') {
        container.removeChild(fieldRows[i]);
      }
    }

    // Ensure there's always at least one empty field at the end
    const remainingInputs = container.querySelectorAll('input');
    const lastInput = remainingInputs[remainingInputs.length - 1];
    if (lastInput && lastInput.value.trim() !== '') {
      this.createFilterField(containerId);
    }
  }

  /**
   * Update filter state from UI
   */
  updateFilterState(containerId) {
    const container = dom.getElement(containerId);
    if (!container) return;

    const inputs = container.querySelectorAll('input');
    const terms = Array.from(inputs)
      .map((input) => input.value.trim())
      .filter((value) => value !== '');

    if (containerId === 'include-filters-container') {
      this.app.state.updateFilter('include', terms);
    } else if (containerId === 'exclude-filters-container') {
      this.app.state.updateFilter('exclude', terms);
    }
  }

  /**
   * Bind filter-related event listeners
   */
  bindEvents() {
    // Deduplication checkbox
    const dedupCheckbox = document.getElementById('deduplicate');
    if (dedupCheckbox) {
      dom.addEvent(dedupCheckbox, 'change', (e) => {
        this.app.state.updateFilter('deduplication', e.target.checked);
        this.applyFilters();
      });
    }

    // Apply filters button
    const applyBtn = document.querySelector('button[onclick="applyFilters()"]');
    if (applyBtn) {
      dom.addEvent(applyBtn, 'click', () => this.applyFilters());
    }

    // Reset filters button
    const resetBtn = document.querySelector('button[onclick="resetFilters()"]');
    if (resetBtn) {
      dom.addEvent(resetBtn, 'click', () => this.resetFilters());
    }
  }

  /**
   * Get current filter terms from state
   */
  getFilterTerms() {
    return this.app.state.getFilterTerms();
  }
}
