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
	main { max-width: 480px; margin: 2rem auto; padding: 0 1rem; font-family: system-ui, sans-serif; }
	.error { color: #c00; }
</style>
