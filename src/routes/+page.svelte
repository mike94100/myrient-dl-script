<script lang="ts">
	import { onMount } from 'svelte';

	// Tauri invoke function - available globally in Tauri environment
	let invoke: any = (window as any).invoke || null;

	let collections: string[] = [];
	let selectedCollection = '';
	let platforms: { name: string; type: string; selected: boolean }[] = [];
	let outputDir = '~/Downloads';
	let isDownloading = false;
	let downloadProgress = '';
	let statusMessage = 'Ready to download';

	// Load collections when component mounts
	onMount(async () => {
		if (!invoke) {
			statusMessage = 'Running in web mode - Tauri backend not available';
			return;
		}

		try {
			// Get available collections from the backend
			const result = await invoke('get_collections');
			collections = result as string[];
		} catch (error) {
			console.error('Failed to load collections:', error);
			statusMessage = 'Failed to load collections';
		}
	});

	// Handle collection selection
	async function onCollectionChange() {
		console.log('Collection changed to:', selectedCollection);
		if (!selectedCollection) {
			platforms = [];
			return;
		}

		if (!invoke) {
			console.log('No invoke function available');
			statusMessage = 'Tauri backend not available';
			return;
		}

		try {
			console.log('Calling get_platforms for collection:', selectedCollection);
			// Get platforms for selected collection
			const result = await invoke('get_platforms', { collection: selectedCollection });
			console.log('get_platforms result:', result);
			platforms = (result as any[]).map(p => ({
				name: p.name,
				type: p.type,
				selected: false
			}));
			console.log('Platforms loaded:', platforms);
		} catch (error) {
			console.error('Failed to load platforms:', error);
			statusMessage = 'Failed to load platforms';
		}
	}

	// Toggle platform selection
	function togglePlatform(index: number) {
		platforms[index].selected = !platforms[index].selected;
		platforms = [...platforms]; // Trigger reactivity
	}

	// Select/deselect all platforms
	function selectAll() {
		const allSelected = platforms.every(p => p.selected);
		platforms = platforms.map(p => ({ ...p, selected: !allSelected }));
	}

	// Start download
	async function startDownload() {
		console.log('Download button clicked');
		console.log('Selected collection:', selectedCollection);
		console.log('Selected platforms:', platforms.filter(p => p.selected));

		if (!selectedCollection || !platforms.some(p => p.selected)) {
			statusMessage = 'Please select a collection and at least one platform';
			console.log('Validation failed - missing collection or platforms');
			return;
		}

		if (!invoke) {
			statusMessage = 'Tauri backend not available';
			console.log('No invoke function available');
			return;
		}

		isDownloading = true;
		statusMessage = 'Starting download...';

		try {
			const selectedPlatforms = platforms.filter(p => p.selected).map(p => p.name);
			console.log('Calling download_collection with:', {
				collection: selectedCollection,
				platforms: selectedPlatforms,
				outputDir: outputDir
			});

			// Call backend download function
			const result = await invoke('download_collection', {
				collection: selectedCollection,
				platforms: selectedPlatforms,
				outputDir: outputDir
			});

			console.log('Download completed with result:', result);
			statusMessage = `Download completed! Downloaded ${selectedPlatforms.length} platform(s).`;
		} catch (error) {
			console.error('Download failed:', error);
			statusMessage = `Download failed: ${error}`;
		} finally {
			isDownloading = false;
		}
	}

	// Browse for output directory
	async function browseOutputDir() {
		console.log('Browse button clicked');

		if (!invoke) {
			console.log('No invoke function available');
			return;
		}

		try {
			console.log('Calling select_folder...');
			const selected = await invoke('select_folder');
			console.log('select_folder result:', selected);
			if (selected) {
				outputDir = selected as string;
				console.log('Output directory updated to:', outputDir);
			}
		} catch (error) {
			console.error('Failed to select folder:', error);
		}
	}
</script>

<main class="container">
	<header>
		<h1>🎮 ROMs as Code</h1>
		<p>Download ROM and BIOS collections from Myrient</p>
	</header>

	<div class="content">
		<!-- Collection Selection -->
		<section class="section">
			<h2>Collection</h2>
			<select bind:value={selectedCollection} on:change={onCollectionChange}>
				<option value="">Select a collection...</option>
				{#each collections as collection}
					<option value={collection}>{collection}</option>
				{/each}
			</select>
		</section>

		<!-- Output Directory -->
		<section class="section">
			<h2>Output Directory</h2>
			<div class="output-dir">
				<input type="text" bind:value={outputDir} placeholder="Select output directory..." />
				<button on:click={browseOutputDir}>Browse</button>
			</div>
		</section>

		<!-- Platforms Selection -->
		{#if platforms.length > 0}
			<section class="section">
				<div class="platforms-header">
					<h2>Platforms</h2>
					<button on:click={selectAll} class="secondary">
						{platforms.every(p => p.selected) ? 'Clear All' : 'Select All'}
					</button>
				</div>

				<div class="platforms-grid">
					{#each platforms as platform, i}
						<label class="platform-item" class:selected={platform.selected}>
							<input
								type="checkbox"
								bind:checked={platform.selected}
								on:change={() => togglePlatform(i)}
							/>
							<span class="platform-name">{platform.name}</span>
							<span class="platform-type">{platform.type}</span>
						</label>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Download Button -->
		<section class="section">
			<button
				on:click={startDownload}
				disabled={isDownloading}
				class="primary download-btn"
			>
				{#if isDownloading}
					⏳ Downloading...
				{:else}
					🚀 Download
				{/if}
			</button>
		</section>

		<!-- Status -->
		<section class="section">
			<div class="status">
				<p>{statusMessage}</p>
				{#if downloadProgress}
					<div class="progress-bar">
						<div class="progress-fill" style="width: {downloadProgress}%"></div>
					</div>
				{/if}
			</div>
		</section>
	</div>
</main>

<style>
	.container {
		max-width: 900px;
		margin: 0 auto;
		padding: 20px;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
	}

	header {
		text-align: center;
		margin-bottom: 40px;
	}

	header h1 {
		margin: 0 0 10px 0;
		color: #1f2937;
		font-size: 2.5rem;
	}

	header p {
		color: #6b7280;
		font-size: 1.1rem;
		margin: 0;
	}

	.section {
		margin-bottom: 30px;
	}

	.section h2 {
		margin: 0 0 15px 0;
		color: #1f2937;
		font-size: 1.3rem;
		font-weight: 600;
	}

	select, input[type="text"] {
		width: 100%;
		padding: 12px;
		border: 2px solid #d1d5db;
		border-radius: 8px;
		font-size: 16px;
		transition: border-color 0.2s;
	}

	select:focus, input[type="text"]:focus {
		outline: none;
		border-color: #3b82f6;
	}

	.output-dir {
		display: flex;
		gap: 10px;
	}

	.output-dir input {
		flex: 1;
	}

	.output-dir button {
		padding: 12px 20px;
		background: #f3f4f6;
		border: 2px solid #d1d5db;
		border-radius: 8px;
		cursor: pointer;
		font-size: 14px;
		transition: all 0.2s;
	}

	.output-dir button:hover {
		background: #e5e7eb;
		border-color: #9ca3af;
	}

	.platforms-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 15px;
	}

	.platforms-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
		gap: 12px;
	}

	.platform-item {
		display: flex;
		align-items: center;
		padding: 12px;
		border: 2px solid #d1d5db;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.2s;
		background: white;
	}

	.platform-item:hover {
		border-color: #9ca3af;
	}

	.platform-item.selected {
		border-color: #3b82f6;
		background: #eff6ff;
	}

	.platform-item input[type="checkbox"] {
		margin-right: 12px;
		width: 18px;
		height: 18px;
	}

	.platform-name {
		flex: 1;
		font-weight: 500;
		color: #1f2937;
	}

	.platform-type {
		font-size: 0.85rem;
		color: #6b7280;
		background: #f3f4f6;
		padding: 2px 8px;
		border-radius: 12px;
		text-transform: uppercase;
		font-weight: 500;
	}

	button.primary, button.secondary {
		padding: 14px 28px;
		border: none;
		border-radius: 8px;
		font-size: 16px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s;
	}

	button.primary {
		background: #3b82f6;
		color: white;
	}

	button.primary:hover:not(:disabled) {
		background: #2563eb;
	}

	button.primary:disabled {
		background: #9ca3af;
		cursor: not-allowed;
	}

	button.secondary {
		background: #f3f4f6;
		color: #374151;
		border: 2px solid #d1d5db;
	}

	button.secondary:hover {
		background: #e5e7eb;
		border-color: #9ca3af;
	}

	.download-btn {
		width: 100%;
		font-size: 18px;
		padding: 18px;
	}

	.status {
		padding: 16px;
		background: #f8fafc;
		border-radius: 8px;
		border: 1px solid #e2e8f0;
	}

	.status p {
		margin: 0;
		color: #374151;
		font-size: 14px;
	}

	.progress-bar {
		margin-top: 12px;
		width: 100%;
		height: 8px;
		background: #e2e8f0;
		border-radius: 4px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: #3b82f6;
		transition: width 0.3s ease;
	}
</style>
