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
	import { createTopic } from '$lib/api/topics';
	import type { TopicCreateResponse } from '$lib/types/topic';

	let defaultTitle = '';
	let creatorEmail = '';
	let result: TopicCreateResponse | null = null;
	let error = '';
	let loading = false;

	async function handleSubmit() {
		if (!defaultTitle.trim()) return;
		loading = true;
		error = '';
		try {
			result = await createTopic(defaultTitle, creatorEmail || undefined);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create topic';
		} finally {
			loading = false;
		}
	}
</script>

<main>
	<h1>Weft</h1>
	<p class="tagline">Private updates for personal networks.</p>

	{#if result}
		<div class="success">
			<h2>Topic created!</h2>
			{#if creatorEmail}
				<p>Check your email for the magic link to manage your topic.</p>
			{:else}
				<p><strong>Bookmark this link</strong> — it's the only way to access your topic:</p>
				<a class="magic-link" href={result.magic_link}>{result.magic_link}</a>
			{/if}
		</div>
	{:else}
		<form on:submit|preventDefault={handleSubmit}>
			<label>
				Topic title
				<input type="text" bind:value={defaultTitle} placeholder="e.g. Family medical update" required />
			</label>
			<label>
				Your email (optional)
				<input type="email" bind:value={creatorEmail} placeholder="you@example.com" />
			</label>
			{#if error}<p class="error">{error}</p>{/if}
			<button type="submit" disabled={loading}>{loading ? 'Creating...' : 'Create Topic'}</button>
		</form>
	{/if}
</main>

<style>
	main { max-width: var(--content-width); margin: 3rem auto; padding: 3rem 1.5rem; }
	h1 { margin-bottom: 0.25rem; font-size: var(--text-2xl); font-family: var(--font-display); }
	.tagline { color: var(--color-text-secondary); margin-top: 0.25rem; margin-bottom: 0; }
	form { display: flex; flex-direction: column; gap: 1rem; margin-top: 1.5rem; }
	label { display: flex; flex-direction: column; gap: 0.25rem; font-weight: 500; }
	input { padding: 0.5rem; border: 1px solid var(--color-border); border-radius: 4px; font-size: var(--text-base); }
	button { padding: 0.6rem 1.2rem; background: var(--color-text); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: var(--text-base); transition: background 0.15s; }
	button:hover:not(:disabled) { background: var(--color-accent); }
	button:disabled { opacity: 0.5; }
	.error { color: var(--color-danger); margin: 0; }
	.success { background: var(--color-success-bg); border: 1px solid var(--color-success-border); padding: 1rem; border-radius: 4px; margin-top: 1.5rem; }
	.magic-link { word-break: break-all; font-family: monospace; display: block; background: var(--color-accent-light); padding: 0.5rem 0.75rem; border-radius: 4px; color: var(--color-accent); margin-top: 0.5rem; }
</style>
