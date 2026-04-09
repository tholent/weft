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
	import { session } from '$lib/stores/session';
	import { topic, updates } from '$lib/stores/topic';
	import { getTopic } from '$lib/api/topics';
	import { getFeed } from '$lib/api/updates';
	import UpdateCard from '$lib/components/UpdateCard.svelte';
	import ComposeBox from '$lib/components/ComposeBox.svelte';
	import ReplyThread from '$lib/components/ReplyThread.svelte';
	import { getReplies, createReply } from '$lib/api/replies';
	import type { Reply } from '$lib/types/reply';

	let replyingTo: string | null = null;
	let repliesMap: Record<string, Reply[]> = {};
	let loading = true;

	onMount(async () => {
		if (!$session.topicId) return;
		try {
			const t = await getTopic($session.topicId);
			topic.set(t);
			const feed = await getFeed($session.topicId);
			updates.set(feed);
		} finally {
			loading = false;
		}
	});

	async function loadReplies(updateId: string) {
		if (!$session.topicId) return;
		repliesMap[updateId] = await getReplies($session.topicId, updateId);
		repliesMap = repliesMap;
	}

	async function handleReply(updateId: string, data: { body: string; wants_to_share: boolean }) {
		if (!$session.topicId) return;
		await createReply($session.topicId, updateId, data.body, data.wants_to_share);
		await loadReplies(updateId);
		replyingTo = null;
	}
</script>

<main>
	{#if loading}
		<p>Loading...</p>
	{:else if $topic}
		<h1>{$topic.scoped_title || $topic.default_title}</h1>
		{#each $updates as update (update.id)}
			<UpdateCard {update} canReply={true} canEdit={false} canDelete={false} />
			<button class="reply-btn" on:click={() => { replyingTo = update.id; loadReplies(update.id); }}>
				Reply ({update.reply_count})
			</button>
			{#if replyingTo === update.id}
				<ComposeBox mode="reply" onSubmit={(d) => handleReply(update.id, d as { body: string; wants_to_share: boolean })} />
			{/if}
			{#if repliesMap[update.id]}
				<ReplyThread replies={repliesMap[update.id]} isModerator={false} />
			{/if}
		{/each}
		{#if $updates.length === 0}
			<p>No updates yet.</p>
		{/if}
	{/if}
</main>

<style>
	main { max-width: var(--content-width); margin: 2rem auto; padding: 0 1rem; }
	.reply-btn { background: none; border: 1px solid var(--color-border); border-radius: 4px; padding: 0.25rem 0.75rem; cursor: pointer; margin: 0.5rem 0; }
</style>
