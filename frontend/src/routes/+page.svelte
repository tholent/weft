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
	<header class="hero">
		<h1>Weft</h1>
		<p class="tagline">Private updates for the people you trust.<br />Ephemeral by design.</p>
	</header>

	<div class="divider"></div>

	{#if result}
		<div class="success">
			<div class="success-icon">✓</div>
			<h2>Topic created</h2>
			{#if creatorEmail}
				<p>Check your email for the link to manage your topic.</p>
			{:else}
				<p><strong>Bookmark this link</strong> — it's the only way back in:</p>
				<a class="magic-link" href={result.magic_link}>{result.magic_link}</a>
			{/if}
		</div>
	{:else}
		<form on:submit|preventDefault={handleSubmit}>
			<label>
				<span class="field-label">What's the topic?</span>
				<input
					type="text"
					bind:value={defaultTitle}
					placeholder="e.g. Dad's recovery update"
					required
				/>
			</label>
			<label>
				<span class="field-label">
					Your email
					<span class="field-hint">— optional, we'll send you the link</span>
				</span>
				<input type="email" bind:value={creatorEmail} placeholder="you@example.com" />
			</label>
			{#if error}<p class="error">{error}</p>{/if}
			<div class="form-footer">
				<button type="submit" disabled={loading}>
					{loading ? 'Creating…' : 'Begin'}
					{#if !loading}<span class="arrow">→</span>{/if}
				</button>
				<p class="privacy-note">No account. No tracking. All contact info purged when you're done.</p>
			</div>
		</form>
	{/if}
</main>

<style>
	main {
		max-width: 540px;
		margin: 5rem auto 3rem;
		padding: 0 1.5rem;
	}

	/* ── Hero ── */
	.hero {
		margin-bottom: 2rem;
	}

	h1 {
		font-family: var(--font-display);
		font-size: 4.5rem;
		font-weight: 400;
		font-style: italic;
		letter-spacing: -0.02em;
		line-height: 1;
		margin: 0 0 0.75rem;
		color: var(--color-text);
	}

	.tagline {
		font-family: var(--font-body);
		font-size: var(--text-lg);
		color: var(--color-text-secondary);
		line-height: 1.55;
		margin: 0;
	}

	/* ── Orange rule separator ── */
	.divider {
		width: 2.5rem;
		height: 2px;
		background: var(--color-accent);
		margin: 0 0 2.5rem;
	}

	/* ── Form ── */
	form {
		display: flex;
		flex-direction: column;
		gap: 1.1rem;
	}

	label {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}

	.field-label {
		font-size: var(--text-sm);
		font-weight: 500;
		color: var(--color-text);
		letter-spacing: 0.01em;
	}

	.field-hint {
		font-weight: 400;
		color: var(--color-text-muted);
	}

	input {
		padding: 0.6rem 0.75rem;
		border: 1px solid var(--color-border);
		border-radius: 2px;
		font-size: var(--text-base);
		background: var(--color-surface);
		color: var(--color-text);
		transition: border-color 0.15s, box-shadow 0.15s, transform 0.1s;
	}

	input:focus {
		transform: translateY(-1px);
	}

	.form-footer {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		margin-top: 0.25rem;
	}

	button[type='submit'] {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		align-self: flex-start;
		padding: 0.65rem 1.5rem;
		background: var(--color-accent);
		color: white;
		border: none;
		border-radius: 2px;
		cursor: pointer;
		font-size: var(--text-base);
		font-weight: 500;
		letter-spacing: 0.02em;
		transition: background 0.15s, transform 0.1s;
	}

	button[type='submit']:hover:not(:disabled) {
		background: var(--color-accent-dark);
		transform: translateY(-1px);
	}

	button[type='submit']:disabled {
		opacity: 0.55;
		cursor: default;
	}

	.arrow {
		font-style: normal;
		opacity: 0.8;
	}

	.privacy-note {
		font-size: var(--text-xs);
		color: var(--color-text-muted);
		margin: 0;
		line-height: 1.5;
	}

	.error {
		color: var(--color-danger);
		font-size: var(--text-sm);
		margin: 0;
	}

	/* ── Success state ── */
	.success {
		background: var(--color-success-bg);
		border: 1px solid var(--color-success-border);
		border-radius: 4px;
		padding: 1.5rem;
	}

	.success-icon {
		width: 2rem;
		height: 2rem;
		background: #16a34a;
		color: white;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.8rem;
		font-weight: 700;
		margin-bottom: 0.75rem;
	}

	.success h2 {
		font-family: var(--font-display);
		font-size: var(--text-xl);
		margin: 0 0 0.5rem;
	}

	.success p {
		margin: 0 0 0.5rem;
		font-size: var(--text-sm);
		color: var(--color-text-secondary);
	}

	.magic-link {
		word-break: break-all;
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		display: block;
		background: var(--color-accent-light);
		padding: 0.6rem 0.85rem;
		border-radius: 2px;
		color: var(--color-accent);
		margin-top: 0.5rem;
		line-height: 1.6;
		border: 1px solid color-mix(in srgb, var(--color-accent) 25%, transparent);
	}
</style>
