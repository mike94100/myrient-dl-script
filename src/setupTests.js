// Jest setup for testing

// Mock fetch for tests
global.fetch = jest.fn();

// Mock URL.createObjectURL and URL.revokeObjectURL
global.URL.createObjectURL = jest.fn(() => 'mocked-url');
global.URL.revokeObjectURL = jest.fn();

// Mock Blob
global.Blob = jest.fn((content, options) => ({
  content,
  options,
  size: content ? content.join('').length : 0
}));

// Mock console methods for cleaner test output
const originalConsole = { ...console };
beforeAll(() => {
  console.log = jest.fn();
  console.warn = jest.fn();
  console.error = jest.fn();
});

afterAll(() => {
  Object.assign(console, originalConsole);
});

// Setup DOM elements that components expect to exist
document.body.innerHTML = `
  <div id="platform-checkboxes"></div>
  <div id="collection-title"></div>
  <div id="collection-description"></div>
  <div id="total-stats-text"></div>
  <div id="platform-sections"></div>
  <div id="include-filters-container"></div>
  <div id="exclude-filters-container"></div>
  <input id="deduplicate" type="checkbox" checked>
  <div id="results-tab-btn" style="display: none;"></div>
  <div id="collection-info" style="display: block;"></div>
`;

// Mock metadata for tests
global.mockMetadata = {
  platforms: {
    'nes': {
      manufacturer: 'Nintendo',
      console: 'NES'
    },
    'snes': {
      manufacturer: 'Nintendo',
      console: 'SNES'
    }
  }
};
