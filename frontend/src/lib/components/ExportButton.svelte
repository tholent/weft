<!--
  Copyright 2026 Chris Wells <chris@tholent.com>

  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
-->

<script lang="ts">
	import { downloadTopicExport } from '$lib/api/export';

	export let topicId: string;

	let loading = false;
	let error: string | null = null;

	async function handleExport() {
		loading = true;
		error = null;
		try {
			await downloadTopicExport(topicId);
		} catch {
			error = 'Export failed. Please try again.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="export-wrap">
	<button class="export-btn" on:click={handleExport} disabled={loading}>
		{loading ? 'Exporting...' : 'Export Topic Data'}
	</button>
	{#if error}
		<p class="error-text">{error}</p>
	{/if}
</div>

<style>
	.export-wrap {
		display: inline-flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.export-btn {
		padding: 0.5rem 1rem;
		background: var(--color-surface, #fff);
		border: 1px solid var(--color-border, #e5e7eb);
		border-radius: 0.375rem;
		font-size: 0.875rem;
		cursor: pointer;
		color: var(--color-text, #111827);
		transition: background 0.15s;
	}

	.export-btn:hover:not(:disabled) {
		background: var(--color-hover, #f3f4f6);
	}

	.export-btn:disabled {
		opacity: 0.6;
		cursor: wait;
	}

	.error-text {
		font-size: 0.75rem;
		color: var(--color-error, #dc2626);
		margin: 0;
	}
</style>
