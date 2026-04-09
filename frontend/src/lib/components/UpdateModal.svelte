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
	import type { Update } from '$lib/types/update';
	import type { Circle } from '$lib/types/circle';
	import type { Reply } from '$lib/types/reply';
	import ReplyThread from '$lib/components/ReplyThread.svelte';
	import { getReplies } from '$lib/api/replies';

	export let update: Update;
	export let circles: Circle[];
	export let isModerator: boolean;
	export let topicId: string;
	export let onClose: () => void;

	let replies: Reply[] = [];

	$: circleNames = update.circle_ids
		.map((id) => circles.find((c) => c.id === id)?.name)
		.filter((name): name is string => name !== undefined);

	onMount(async () => {
		replies = await getReplies(topicId, update.id);
	});

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) onClose();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
<div class="backdrop" on:click={handleBackdropClick}>
	<div class="modal" role="dialog" aria-modal="true">
		<button class="close" on:click={onClose}>✕</button>

		<p class="body">{update.body}</p>

		<div class="meta">
			<span>{update.author_handle || 'Anonymous'}</span>
			<span>{new Date(update.created_at).toLocaleString()}</span>
			{#if update.edited_at}<span class="edited">(edited)</span>{/if}
		</div>

		{#if circleNames.length > 0}
			<div class="circles">
				{#each circleNames as name}
					<span class="pill">{name}</span>
				{/each}
			</div>
		{/if}

		<div class="replies-section">
			<h3>Replies ({update.reply_count})</h3>
			{#if replies.length > 0}
				<ReplyThread {replies} {isModerator} />
			{:else}
				<p class="empty">No replies yet.</p>
			{/if}
		</div>
	</div>
</div>

<style>
	.backdrop {
		position: fixed; inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex; align-items: center; justify-content: center;
		z-index: 100;
	}
	.modal {
		background: var(--color-surface); border-radius: 6px;
		padding: 1.5rem; width: min(600px, 90vw);
		max-height: 80vh; overflow-y: auto;
		position: relative;
		animation: modal-in 0.15s ease-out;
	}
	@keyframes modal-in {
		from { opacity: 0; transform: translateY(6px); }
		to { opacity: 1; transform: translateY(0); }
	}
	.close {
		position: absolute; top: 0.75rem; right: 0.75rem;
		background: none; border: none; font-size: 1rem;
		cursor: pointer; color: var(--color-text-secondary); line-height: 1;
	}
	.body { margin: 0 0 0.75rem; line-height: 1.6; white-space: pre-wrap; }
	.meta { font-size: var(--text-sm); color: var(--color-text-secondary); display: flex; gap: 0.75rem; flex-wrap: wrap; }
	.edited { font-style: italic; }
	.circles { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.5rem; }
	.pill { font-size: var(--text-xs); background: var(--color-accent-light); border-radius: 999px; padding: 0.1rem 0.6rem; color: var(--color-accent); border: 1px solid #f0d0b0; }
	.replies-section { margin-top: 1.25rem; border-top: 1px solid var(--color-border); padding-top: 1rem; }
	.replies-section h3 { margin: 0 0 0.75rem; font-size: 0.95rem; }
	.empty { color: var(--color-text-muted); font-size: var(--text-sm); }
</style>
