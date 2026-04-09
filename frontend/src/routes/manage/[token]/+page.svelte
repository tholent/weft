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
	import { session, isModerator, isAdmin, isCreator } from '$lib/stores/session';
	import { topic, updates, circles, members } from '$lib/stores/topic';
	import { getTopic, closeTopic } from '$lib/api/topics';
	import { getFeed, createUpdate } from '$lib/api/updates';
	import { listCircles } from '$lib/api/circles';
	import { listMembers } from '$lib/api/members';
	import UpdateCard from '$lib/components/UpdateCard.svelte';
	import UpdateModal from '$lib/components/UpdateModal.svelte';
	import ComposeBox from '$lib/components/ComposeBox.svelte';
	import CircleManager from '$lib/components/CircleManager.svelte';
	import MemberRow from '$lib/components/MemberRow.svelte';
	import TransferBanner from '$lib/components/TransferBanner.svelte';
	import type { Update } from '$lib/types/update';

	let activeTab: 'updates' | 'members' | 'circles' | 'settings' = 'updates';
	let loading = true;
	let selectedUpdate: Update | null = null;

	onMount(async () => {
		if (!$session.topicId) return;
		try {
			const [t, feed, c, m] = await Promise.all([
				getTopic($session.topicId),
				getFeed($session.topicId),
				listCircles($session.topicId),
				listMembers($session.topicId)
			]);
			topic.set(t);
			updates.set(feed);
			circles.set(c);
			members.set(m);
		} finally {
			loading = false;
		}
	});

	async function handleNewUpdate(data: Record<string, unknown>) {
		if (!$session.topicId) return;
		await createUpdate($session.topicId, data.body as string, data.circle_ids as string[]);
		updates.set(await getFeed($session.topicId));
	}

	async function handleClose() {
		if (!$session.topicId || !confirm('Close this topic? All emails will be purged.')) return;
		await closeTopic($session.topicId);
		topic.set(await getTopic($session.topicId));
	}
</script>

<main>
	{#if loading}
		<p>Loading...</p>
	{:else if $topic}
		<h1>{$topic.default_title}</h1>

		<nav>
			<button class:active={activeTab === 'updates'} on:click={() => (activeTab = 'updates')}>Updates</button>
			<button class:active={activeTab === 'members'} on:click={() => (activeTab = 'members')}>Members</button>
			{#if $isAdmin}
				<button class:active={activeTab === 'circles'} on:click={() => (activeTab = 'circles')}>Circles</button>
				<button class:active={activeTab === 'settings'} on:click={() => (activeTab = 'settings')}>Settings</button>
			{/if}
		</nav>

		{#if activeTab === 'updates'}
			{#if $isModerator}
				<h2>Post Update</h2>
				<ComposeBox mode="update" targetCircles={$circles} onSubmit={handleNewUpdate} />
			{/if}
			{#each $updates as update (update.id)}
				<UpdateCard {update} circles={$circles} onClick={() => (selectedUpdate = update)} />
			{/each}
		{:else if activeTab === 'members'}
			<h2>Members</h2>
			{#each $members as member (member.id)}
				<MemberRow {member} circles={$circles} viewerRole={$session.role || 'recipient'} />
			{/each}
		{:else if activeTab === 'circles'}
			<CircleManager />
		{:else if activeTab === 'settings'}
			<h2>Settings</h2>
			<TransferBanner />
			{#if $isCreator}
				<button class="danger" on:click={handleClose}>Close Topic</button>
			{/if}
		{/if}
	{/if}
</main>

{#if selectedUpdate && $session.topicId}
	<UpdateModal
		update={selectedUpdate}
		circles={$circles}
		isModerator={$isModerator}
		topicId={$session.topicId}
		onClose={() => (selectedUpdate = null)}
	/>
{/if}

<style>
	main { max-width: var(--content-width); margin: 2rem auto; padding: 0 1rem; }
	h1 { padding-bottom: 1rem; border-bottom: 1px solid var(--color-border); margin-bottom: 1.5rem; }
	nav { display: flex; gap: 0.5rem; margin: 1rem 0; border-bottom: 1px solid var(--color-border); padding-bottom: 0.5rem; }
	nav button {
		background: none; border: none; border-bottom: 2px solid transparent;
		padding: 0.5rem 1rem; cursor: pointer; border-radius: 0;
		letter-spacing: 0.03em; text-transform: uppercase; font-size: var(--text-xs);
		color: var(--color-text-secondary);
		margin-bottom: -1px;
	}
	nav button.active { border-bottom-color: var(--color-accent); color: var(--color-accent); }
	.danger { background: var(--color-danger); color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; margin-top: 1rem; }
</style>
