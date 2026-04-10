<!--
  Copyright 2026 Chris Wells <chris@tholern.com>

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
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { verifyMagicLink } from '$lib/api/auth';
	import { login } from '$lib/stores/session';

	let error = '';
	let loading = true;

	onMount(async () => {
		const token = $page.url.searchParams.get('t');
		if (!token) {
			error = 'No token provided.';
			loading = false;
			return;
		}
		try {
			const auth = await verifyMagicLink(token);
			login(auth.token, auth.member_id, auth.role, auth.topic_id);
			if (auth.role === 'recipient') {
				goto(`/topic/${auth.token}`);
			} else {
				goto(`/manage/${auth.token}`);
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Invalid or expired link.';
			loading = false;
		}
	});
</script>

<main>
	{#if loading}
		<div class="state-wrap">
			<div class="spinner" aria-label="Verifying"></div>
			<p class="state-text">Verifying your link…</p>
		</div>
	{:else if error}
		<div class="state-wrap">
			<div class="error-icon">!</div>
			<h2>Link error</h2>
			<p class="error-msg">{error}</p>
			<a class="home-link" href="/">← Back to home</a>
		</div>
	{/if}
</main>

<style>
	main {
		max-width: var(--content-width);
		margin: 6rem auto;
		padding: 0 1.5rem;
		text-align: center;
	}

	.state-wrap {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
	}

	/* ── Loading spinner ── */
	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.spinner {
		width: 2rem;
		height: 2rem;
		border: 2px solid var(--color-border);
		border-top-color: var(--color-accent);
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}

	.state-text {
		font-family: var(--font-body);
		font-size: var(--text-lg);
		font-style: italic;
		color: var(--color-text-muted);
		margin: 0;
	}

	/* ── Error state ── */
	.error-icon {
		width: 2.5rem;
		height: 2.5rem;
		border-radius: 50%;
		background: var(--color-danger-bg);
		border: 1px solid var(--color-danger);
		color: var(--color-danger);
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: 700;
		font-size: 1rem;
	}

	h2 {
		font-family: var(--font-display);
		font-size: var(--text-2xl);
		font-weight: 400;
		margin: 0;
	}

	.error-msg {
		color: var(--color-text-secondary);
		font-size: var(--text-sm);
		margin: 0;
	}

	.home-link {
		font-size: var(--text-sm);
		color: var(--color-accent);
		text-decoration: none;
		border-bottom: 1px solid color-mix(in srgb, var(--color-accent) 40%, transparent);
		padding-bottom: 1px;
		transition: border-color 0.15s;
	}

	.home-link:hover {
		border-color: var(--color-accent);
	}
</style>
