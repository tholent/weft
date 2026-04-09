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
	<p>Private, ephemeral announcements for your personal network.</p>

	{#if result}
		<div class="success">
			<h2>Topic created!</h2>
			{#if creatorEmail}
				<p>Check your email for the magic link to manage your topic.</p>
			{:else}
				<p><strong>Bookmark this link</strong> — it's the only way to access your topic:</p>
				<a href={result.magic_link}>{result.magic_link}</a>
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
	main { max-width: 480px; margin: 2rem auto; padding: 0 1rem; font-family: system-ui, sans-serif; }
	h1 { margin-bottom: 0.25rem; }
	form { display: flex; flex-direction: column; gap: 1rem; margin-top: 1.5rem; }
	label { display: flex; flex-direction: column; gap: 0.25rem; font-weight: 500; }
	input { padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; font-size: 1rem; }
	button { padding: 0.6rem 1.2rem; background: #111; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }
	button:disabled { opacity: 0.5; }
	.error { color: #c00; margin: 0; }
	.success { background: #f0fdf4; border: 1px solid #86efac; padding: 1rem; border-radius: 4px; margin-top: 1.5rem; }
	.success a { word-break: break-all; }
</style>
