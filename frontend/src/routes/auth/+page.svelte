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
			error = 'No token provided';
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
			error = e instanceof Error ? e.message : 'Invalid or expired link';
			loading = false;
		}
	});
</script>

<main>
	{#if loading}
		<p>Verifying your link...</p>
	{:else if error}
		<h2>Link Error</h2>
		<p class="error">{error}</p>
		<a href="/">Go home</a>
	{/if}
</main>

<style>
	main { max-width: var(--content-width); margin: 2rem auto; padding: 0 1rem; }
	.error { color: var(--color-danger); }
</style>
