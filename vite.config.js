import { defineConfig } from 'vite'

export default defineConfig({
  // Build configuration
  build: {
    // Target modern browsers that support ES2015+
    target: 'es2015',

    // Output directory
    outDir: 'dist',

    // Clean output directory before build
    emptyOutDir: true,

    // Enable source maps for debugging
    sourcemap: true,

    // Minification
    minify: 'terser'
  },

  // Development server configuration
  server: {
    // Port for dev server
    port: 3000,

    // Open browser automatically
    open: true,

    // Hot module replacement
    hmr: true
  },

  // Path resolution
  resolve: {
    // Aliases for cleaner imports
    alias: {
      '@': '/src'
    }
  }
})
