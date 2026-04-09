<script lang="ts">
	import { onMount } from 'svelte';
	import { session, isModerator, isAdmin, isCreator } from '$lib/stores/session';
	import { topic, updates, circles, members } from '$lib/stores/topic';
	import { getTopic, closeTopic } from '$lib/api/topics';
	import { getFeed, createUpdate } from '$lib/api/updates';
	import { listCircles } from '$lib/api/circles';
	import { listMembers } from '$lib/api/members';
	import UpdateCard from '$lib/components/UpdateCard.svelte';
	import ComposeBox from '$lib/components/ComposeBox.svelte';
	import CircleManager from '$lib/components/CircleManager.svelte';
	import MemberRow from '$lib/components/MemberRow.svelte';
	import TransferBanner from '$lib/components/TransferBanner.svelte';
	import ReplyThread from '$lib/components/ReplyThread.svelte';
	import { getReplies } from '$lib/api/replies';
	import type { Reply } from '$lib/types/reply';

	let activeTab: 'updates' | 'members' | 'circles' | 'settings' = 'updates';
	let loading = true;
	let repliesMap: Record<string, Reply[]> = {};

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

	async function loadReplies(updateId: string) {
		if (!$session.topicId) return;
		repliesMap[updateId] = await getReplies($session.topicId, updateId);
		repliesMap = repliesMap;
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
				<UpdateCard
					{update}
					canReply={true}
					canEdit={update.author_member_id === $session.memberId}
					canDelete={update.author_member_id === $session.memberId || $isAdmin}
				/>
				<button class="reply-btn" on:click={() => loadReplies(update.id)}>
					Replies ({update.reply_count})
				</button>
				{#if repliesMap[update.id]}
					<ReplyThread replies={repliesMap[update.id]} isModerator={$isModerator} />
				{/if}
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

<style>
	main { max-width: 720px; margin: 2rem auto; padding: 0 1rem; font-family: system-ui, sans-serif; }
	nav { display: flex; gap: 0.5rem; margin: 1rem 0; border-bottom: 1px solid #ddd; padding-bottom: 0.5rem; }
	nav button { background: none; border: none; padding: 0.5rem 1rem; cursor: pointer; border-radius: 4px; }
	nav button.active { background: #111; color: white; }
	.reply-btn { background: none; border: 1px solid #ccc; border-radius: 4px; padding: 0.25rem 0.75rem; cursor: pointer; margin: 0.5rem 0; }
	.danger { background: #c00; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; margin-top: 1rem; }
</style>
