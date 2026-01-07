import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	build: {
		rollupOptions: {
			external: (id) => {
				// Externalize Tauri APIs - they're only available at runtime
				return id.startsWith('@tauri-apps/');
			}
		}
	}
});
