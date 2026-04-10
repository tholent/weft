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

{#if loading}
	<div class="topic-header topic-header--skeleton">
		<div class="header-inner">
			<div class="skeleton-line" style="width: 55%; height: 2.4rem; border-radius: 3px;"></div>
			<div class="skeleton-line" style="width: 25%; height: 0.75rem; margin-top: 0.75rem; border-radius: 3px;"></div>
		</div>
	</div>
	<div class="feed-wrapper">
		{#each Array(4) as _}
			<div class="skeleton-card">
				<div class="skeleton-line" style="width: 90%"></div>
				<div class="skeleton-line" style="width: 75%"></div>
				<div class="skeleton-line" style="width: 60%"></div>
				<div class="skeleton-meta"></div>
			</div>
		{/each}
	</div>
{:else if $topic}
	<div class="topic-header">
		<div class="header-inner">
			<h1>{$topic.scoped_title || $topic.default_title}</h1>
			<p class="header-sub">Updates from your network</p>
		</div>
	</div>

	<div class="feed-wrapper">
		{#each $updates as update (update.id)}
			<UpdateCard {update} canReply={true} canEdit={false} canDelete={false} />
			<button
				class="reply-btn"
				on:click={() => {
					replyingTo = update.id;
					loadReplies(update.id);
				}}
			>
				{update.reply_count > 0 ? `${update.reply_count} ${update.reply_count === 1 ? 'reply' : 'replies'}` : 'Reply'}
			</button>
			{#if replyingTo === update.id}
				<ComposeBox
					mode="reply"
					onSubmit={(d) => handleReply(update.id, d as { body: string; wants_to_share: boolean })}
				/>
			{/if}
			{#if repliesMap[update.id]}
				<ReplyThread replies={repliesMap[update.id]} isModerator={false} />
			{/if}
		{/each}

		{#if $updates.length === 0}
			<div class="empty-state">
				<p class="empty-headline">Nothing yet.</p>
				<p class="empty-body">This is the quiet before the story begins. Check back soon.</p>
			</div>
		{/if}
	</div>
{/if}

<style>
	/* ── Full-bleed header ── */
	.topic-header {
		background: var(--color-text);
		padding: 2.5rem 0 2rem;
		margin-bottom: 0;
	}

	.topic-header--skeleton {
		background: var(--color-surface-hover);
	}

	.header-inner {
		max-width: var(--content-width);
		margin: 0 auto;
		padding: 0 1.5rem;
	}

	h1 {
		font-family: var(--font-display);
		font-size: var(--text-3xl);
		font-weight: 400;
		color: white;
		margin: 0 0 0.35rem;
		line-height: 1.1;
	}

	.header-sub {
		font-size: var(--text-xs);
		font-family: var(--font-mono);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: rgba(255, 255, 255, 0.5);
		margin: 0;
	}

	/* ── Feed ── */
	.feed-wrapper {
		max-width: var(--content-width);
		margin: 0 auto;
		padding: 1.5rem 1.5rem 3rem;
	}

	/* ── Reply button ── */
	.reply-btn {
		background: none;
		border: 1px solid var(--color-border);
		border-radius: 2px;
		padding: 0.25rem 0.75rem;
		cursor: pointer;
		margin: 0.35rem 0 0.75rem;
		font-size: var(--text-xs);
		font-family: var(--font-ui);
		letter-spacing: 0.03em;
		color: var(--color-text-secondary);
		transition: border-color 0.15s, color 0.15s;
	}

	.reply-btn:hover {
		border-color: var(--color-accent);
		color: var(--color-accent);
	}

	/* ── Empty state ── */
	.empty-state {
		text-align: center;
		padding: 4rem 1rem;
	}

	.empty-headline {
		font-family: var(--font-display);
		font-size: var(--text-2xl);
		font-weight: 400;
		font-style: italic;
		color: var(--color-text-muted);
		margin: 0 0 0.5rem;
	}

	.empty-body {
		font-family: var(--font-body);
		font-size: var(--text-base);
		color: var(--color-text-muted);
		margin: 0;
		font-style: italic;
	}
</style>
