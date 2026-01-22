import { dom, groupPlatformsByManufacturer } from '../utils/index.js';

/**
 * Handles platform selection UI and logic
 */
export class PlatformSelector {
  constructor(app) {
    this.app = app;
    this.container = null;
  }

  /**
   * Initialize the platform selector
   */
  init(containerId = 'platform-checkboxes') {
    this.container = dom.getElement(containerId);
    if (!this.container) return;

    this.render();
    this.bindEvents();
  }

  /**
   * Render the platform selection UI
   */
  render() {
    if (!this.container || !this.app.state.metadata) return;

    dom.clearElement(this.container);

    const { manufacturerGroups, otherPlatforms } = groupPlatformsByManufacturer(
      this.app.state.metadata
    );

    // Sort manufacturers and create sections
    const sortedManufacturers = Object.keys(manufacturerGroups).sort();

    sortedManufacturers.forEach((manufacturer) => {
      const platforms = manufacturerGroups[manufacturer];

      // Skip "Other" for now, we'll handle it at the end
      if (manufacturer === 'Other') return;

      // Only create collapsible section if manufacturer has multiple platforms
      if (platforms.length > 1) {
        this.createManufacturerSection(manufacturer, platforms, true);
      } else {
        // Single platform manufacturer - add to Other group
        otherPlatforms.push(...platforms);
      }
    });

    // Handle "Other" platforms
    if (otherPlatforms.length > 0) {
      this.createManufacturerSection('Other', otherPlatforms, otherPlatforms.length > 1);
    }
  }

  /**
   * Create a manufacturer section
   */
  createManufacturerSection(manufacturer, platforms, collapsible = true) {
    const section = dom.createElement('div', { className: 'manufacturer-section' });

    // Sort platforms within manufacturer
    platforms.sort((a, b) => a.displayName.localeCompare(b.displayName));

    if (collapsible && platforms.length > 1) {
      // Collapsible section for multiple platforms
      section.innerHTML = `
                <h4>${manufacturer} <button class="toggle-btn" data-action="toggle-manufacturer" data-manufacturer="${manufacturer}">+</button></h4>
                <div class="manufacturer-content" id="manufacturer-${manufacturer}" style="display: none;">
                </div>
            `;

      const contentDiv = section.querySelector('.manufacturer-content');
      platforms.forEach((platform) => {
        contentDiv.appendChild(this.createPlatformCheckbox(platform));
      });
    } else {
      // Non-collapsible section for single platform or "Other"
      section.innerHTML = `<h4>${manufacturer}</h4>`;
      platforms.forEach((platform) => {
        section.appendChild(this.createPlatformCheckbox(platform));
      });
    }

    this.container.appendChild(section);
  }

  /**
   * Create a platform checkbox element
   */
  createPlatformCheckbox(platformData) {
    const label = dom.createElement('label', { style: 'display: block; margin: 2px 0;' });

    const checkbox = dom.createElement('input', {
      type: 'checkbox',
      value: platformData.key,
      id: `platform-${platformData.key}`,
    });

    // Set checked state based on current selection
    checkbox.checked = this.app.state.selectedPlatforms.has(platformData.key);

    const span = dom.createElement('span', {
      textContent: platformData.displayName,
      style: 'margin-left: 5px;',
    });

    label.appendChild(checkbox);
    label.appendChild(span);

    return label;
  }

  /**
   * Bind event listeners
   */
  bindEvents() {
    if (!this.container) return;

    // Platform checkbox changes
    dom.addEvent(this.container, 'change', (e) => {
      if (e.target.type === 'checkbox' && e.target.id.startsWith('platform-')) {
        const platformKey = e.target.value;
        this.app.state.togglePlatform(platformKey);
        this.handlePlatformSelection();
      }
    });

    // Manufacturer toggle buttons
    dom.addEvent(this.container, 'click', (e) => {
      if (
        e.target.classList.contains('toggle-btn') &&
        e.target.dataset.action === 'toggle-manufacturer'
      ) {
        const manufacturer = e.target.dataset.manufacturer;
        this.toggleManufacturerSection(manufacturer);
      }
    });
  }

    /**
     * Handle platform selection changes
     */
    handlePlatformSelection() {
        const selectedPlatforms = this.app.state.getSelectedPlatforms();

        if (selectedPlatforms.length === 0) {
            // Hide results tab when no platforms selected
            this.app.tabManager.setResultsTabVisible(false);
            this.app.state.clearPlatformSelection();
            return;
        }

        // Show results tab button (user can manually switch to view results)
        this.app.tabManager.setResultsTabVisible(true);

        // Load collections for selected platforms (but don't switch tabs)
        this.loadSelectedCollections();
    }

  /**
   * Load collections for selected platforms
   */
  async loadSelectedCollections() {
    const selectedPlatforms = this.app.state.getSelectedPlatforms();

    try {
      // Load all selected platforms
      const loadPromises = selectedPlatforms.map(async (platform) => {
        const response = await fetch(`data/${platform}.json`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status} for ${platform}`);
        }
        const data = await response.json();
        const metadata = this.app.state.metadata.platforms[platform];

        const collectionData = {
          platform: platform,
          title: `${metadata.manufacturer} - ${metadata.console} ROM Collection`,
          description: metadata.description,
          files: data.files || data,
        };

        this.app.state.setCollection(platform, collectionData);
      });

      await Promise.all(loadPromises);
      this.app.resultsDisplay.displayCollections();
    } catch (error) {
      console.error('Failed to load collections:', error);
      // Note: Error handling moved to ResultsDisplay.displayCollections
    }
  }

  /**
   * Toggle manufacturer section visibility
   */
  toggleManufacturerSection(manufacturer) {
    const content = document.getElementById(`manufacturer-${manufacturer}`);
    const toggleBtn = content.parentElement.querySelector('.toggle-btn');

    if (content.style.display === 'none') {
      content.style.display = 'block';
      toggleBtn.textContent = '−';
    } else {
      content.style.display = 'none';
      toggleBtn.textContent = '+';
    }
  }
}
