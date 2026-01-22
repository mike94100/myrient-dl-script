# ROM Collection Browser

A modern web application for browsing and downloading ROM collections with advanced filtering and batch download capabilities.

## 🚀 Features

- **Multi-Platform Support**: Browse ROMs across multiple gaming platforms
- **Advanced Filtering**: Include/exclude terms, deduplication, manual overrides
- **Batch Downloads**: Generate Bash/Python scripts for downloading multiple ROMs

## 🛠️ Development Setup

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn

### Installation

```bash
# Clone the repository
git clone https://github.com/mike94100/roms-as-code.git
cd roms-as-code

# Install dependencies
npm install
```

### Development Workflow

```bash
# Start development server with hot reloading
npm run dev

# Open http://localhost:3000 in your browser
```

### Available Scripts

```bash
# Development
npm run dev        # Start development server
npm run watch      # Watch mode for file changes

# Code Quality
npm run lint       # Check code style
npm run lint:fix   # Auto-fix linting issues
npm run format     # Format code with Prettier

# Testing
npm run test       # Run unit tests

# Production
npm run build      # Create production build
npm run clean      # Clean build directory
```

## 🏗️ Project Structure

```
roms-as-code/
├── src/
│   ├── components/        # UI components
│   │   ├── PlatformSelector.js
│   │   ├── FilterManager.js
│   │   ├── ResultsDisplay.js
│   │   └── TabManager.js
│   ├── models/           # Data models
│   │   └── State.js
│   ├── utils/            # Utility functions
│   │   ├── index.js
│   │   ├── index.test.js
│   │   └── setupTests.js
│   └── app.js            # Main application
├── styles/
│   └── main.css          # Application styles
├── templates/            # Download script templates
├── dist/                 # Production build output
├── package.json
├── webpack.config.js
└── README.md
```

## 🏭 Build System

### Vite Configuration

The project uses Vite for development and production builds:
- **ES6 Module Bundling**: Native ES modules in development, optimized bundles for production
- **CSS Processing**: Automatic stylesheet processing and optimization
- **Asset Optimization**: Minification, compression, and tree-shaking
- **Development Server**: Hot reloading and live development

### Development Workflow

```bash
# Start lightning-fast development server
npm run dev

# Build for production
npm run build

# Preview production build locally
npm run preview
```

### Production Build Output

Creates optimized files in the `dist/` directory:
- `index.html` - Optimized HTML with asset references
- `assets/index-[hash].js` - Minified JavaScript bundle (~20KB)
- `assets/index-[hash].js.map` - Source maps for debugging

## 🧪 Testing

The project includes Jest for unit testing:

```bash
npm run test
```

Tests are located alongside source files with `.test.js` extension.

## 🎯 Architecture Overview

### Component Architecture

- **App**: Main coordinator, initializes all components
- **State**: Centralized state management with immutable updates
- **Components**: Modular UI components with single responsibilities
- **Utils**: Shared utility functions and DOM helpers

### Key Patterns

- **Observer Pattern**: Components react to state changes
- **Event Delegation**: Efficient event handling on parent elements
- **Debounced Operations**: Performance optimization for user input
- **Lazy Initialization**: Components initialize only when needed

### State Management

Centralized state with controlled mutations:

```javascript
// State updates trigger component re-renders
app.state.selectPlatform('nes');
app.resultsDisplay.displayCollections();
```

## 📦 Deployment

### Production Build

```bash
npm run build
```

### Serving Static Files

The `dist/` directory contains all files needed for deployment. Serve with any static file server:

```bash
# Using Python
python -m http.server 8000 -d dist

# Using Node.js
npx serve dist

# Using Apache/Nginx
# Copy dist/ contents to web root
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and run tests: `npm run test`
4. Format code: `npm run format`
5. Lint code: `npm run lint`
6. Submit a pull request

## 📄 License

GPL 3.0 - See LICENSE file for details

## AI Developed

Built with AI assistance given my limited programming knowledge. Because of this, I would not recommend using this for any more than a test use case. This is meant as a proof-of-concept for code-as-configuration ROM collections that can be easily downloaded to any device by any user.
