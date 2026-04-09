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
	import { getReplies, createReply, relayReply, dismissReply } from '$lib/api/replies';
	import { editUpdate } from '$lib/api/updates';

	export let update: Update;
	export let circles: Circle[];
	export let isModerator: boolean;
	export let canEdit: boolean = false;
	export let topicId: string;
	export let onClose: () => void;
	export let onUpdate: (updated: Update) => void = () => {};

	let replies: Reply[] = [];
	let replyBody = '';
	let submitting = false;
	let editing = false;
	let editBody = '';
	let editVariants: Record<string, string> = {};

	function startEdit() {
		editBody = update.body;
		editVariants = { ...update.body_variants };
		editing = true;
	}

	async function handleEdit() {
		if (!editBody.trim() || submitting) return;
		submitting = true;
		try {
			const updated = await editUpdate(topicId, update.id, editBody.trim(), editVariants);
			update = { ...update, body: updated.body, body_variants: updated.body_variants, edited_at: updated.edited_at };
			onUpdate(update);
			editing = false;
		} finally {
			submitting = false;
		}
	}

	$: circleNames = update.circle_ids
		.map((id) => circles.find((c) => c.id === id)?.name)
		.filter((name): name is string => name !== undefined);

	$: variantEntries = Object.entries(update.body_variants ?? {})
		.map(([circleId, variantBody]) => ({
			circleId,
			circleName: circles.find((c) => c.id === circleId)?.name ?? circleId,
			body: variantBody
		}));

	onMount(async () => {
		replies = await getReplies(topicId, update.id);
	});

	async function handleReply() {
		if (!replyBody.trim() || submitting) return;
		submitting = true;
		try {
			await createReply(topicId, update.id, replyBody.trim());
			replyBody = '';
			replies = await getReplies(topicId, update.id);
		} finally {
			submitting = false;
		}
	}

	async function handleRelay(replyId: string) {
		await relayReply(topicId, update.id, replyId);
		replies = await getReplies(topicId, update.id);
	}

	async function handleDismiss(replyId: string) {
		await dismissReply(topicId, update.id, replyId);
		replies = await getReplies(topicId, update.id);
	}

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

		{#if editing}
			<textarea class="edit-body" bind:value={editBody} rows="5"></textarea>
			{#if variantEntries.length > 0}
				<div class="variants">
					{#each variantEntries as v}
						<div class="variant">
							<span class="variant-label">{v.circleName}</span>
							<textarea
								class="edit-body variant-edit"
								rows="3"
								bind:value={editVariants[v.circleId]}
							></textarea>
						</div>
					{/each}
				</div>
			{/if}
			<div class="edit-actions">
				<button on:click={handleEdit} disabled={submitting || !editBody.trim()}>
					{submitting ? 'Saving…' : 'Save'}
				</button>
				<button class="cancel" on:click={() => (editing = false)}>Cancel</button>
			</div>
		{:else}
			<p class="body">{update.body}</p>
		{/if}

		<div class="meta">
			<span>{update.author_handle || 'Anonymous'}</span>
			<span>{new Date(update.created_at).toLocaleString()}</span>
			{#if update.edited_at}<span class="edited">(edited)</span>{/if}
			{#if canEdit && !editing}
				<button class="edit-btn" on:click={startEdit}>Edit</button>
			{/if}
		</div>

		{#if circleNames.length > 0}
			<div class="circles">
				{#each circleNames as name}
					<span class="pill">{name}</span>
				{/each}
			</div>
		{/if}

		{#if variantEntries.length > 0}
			<div class="variants">
				{#each variantEntries as v}
					<div class="variant">
						<span class="variant-label">{v.circleName}</span>
						<p class="variant-body">{v.body}</p>
					</div>
				{/each}
			</div>
		{/if}

		<div class="replies-section">
			<h3>Replies ({replies.length})</h3>
			{#if isModerator}
				<div class="compose">
					<textarea
						bind:value={replyBody}
						placeholder="Write a reply…"
						rows="2"
						on:keydown={(e) => e.key === 'Enter' && e.metaKey && handleReply()}
					></textarea>
					<button on:click={handleReply} disabled={submitting || !replyBody.trim()}>
						{submitting ? 'Posting…' : 'Reply'}
					</button>
				</div>
			{/if}
			{#if replies.length > 0}
				<ReplyThread {replies} {isModerator} onRelay={isModerator ? handleRelay : null} onDismiss={isModerator ? handleDismiss : null} />
			{:else}
				<p class="empty">No replies yet.</p>
			{/if}
		</div>
	</div>
</div>

<style>
	.backdrop {
		position: fixed; inset: 0;
		background: rgba(0, 0, 0, 0.35);
		backdrop-filter: blur(4px);
		-webkit-backdrop-filter: blur(4px);
		display: flex; align-items: center; justify-content: center;
		z-index: 100;
	}
	.modal {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 1.5rem; width: min(600px, 90vw);
		max-height: 80vh; overflow-y: auto;
		position: relative;
		animation: modal-in 0.18s ease-out;
		box-shadow: 0 8px 32px rgba(0,0,0,0.12);
		scrollbar-width: thin;
		scrollbar-color: var(--color-border-strong) transparent;
	}
	.modal::-webkit-scrollbar { width: 6px; }
	.modal::-webkit-scrollbar-track { background: transparent; }
	.modal::-webkit-scrollbar-thumb { background: var(--color-border-strong); border-radius: 3px; }
	@keyframes modal-in {
		from { opacity: 0; transform: translateY(6px); }
		to { opacity: 1; transform: translateY(0); }
	}
	.close {
		position: absolute; top: 0.75rem; right: 0.75rem;
		background: none; border: none; font-size: 1rem;
		cursor: pointer; color: var(--color-text-secondary); line-height: 1;
	}
	.body { margin: 0 0 0.75rem; line-height: 1.7; white-space: pre-wrap; font-family: var(--font-display); font-size: var(--text-base); }
	.edit-body { width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); border-radius: 4px; font-family: inherit; font-size: var(--text-base); line-height: 1.6; resize: vertical; margin-bottom: 0.5rem; box-sizing: border-box; }
	.variant-edit { font-size: var(--text-sm); margin-top: 0.35rem; margin-bottom: 0; }
	.edit-actions { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }
	.edit-actions button { padding: 0.35rem 0.9rem; border: none; border-radius: 4px; cursor: pointer; font-size: var(--text-sm); transition: background 0.15s; }
	.edit-actions button:not(.cancel) { background: var(--color-text); color: white; }
	.edit-actions button:not(.cancel):hover:not(:disabled) { background: var(--color-accent); }
	.edit-actions button:disabled { opacity: 0.5; cursor: default; }
	.edit-actions button.cancel { background: none; border: 1px solid var(--color-border); color: var(--color-text-secondary); }
	.meta { font-size: var(--text-sm); color: var(--color-text-secondary); display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; }
	.edited { font-style: italic; }
	.edit-btn { background: none; border: none; color: var(--color-text-secondary); font-size: var(--text-xs); cursor: pointer; padding: 0; text-decoration: underline; }
	.circles { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.5rem; }
	.pill { font-size: var(--text-xs); background: var(--color-accent-light); border-radius: 4px; padding: 0.1rem 0.6rem; color: var(--color-accent); border: 1px solid #f0d0b0; }
	.variants { margin-top: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem; }
	.variant { background: var(--color-accent-light); border-left: 3px solid var(--color-accent); border-radius: 0 4px 4px 0; padding: 0.5rem 0.75rem; }
	.variant-label { font-size: var(--text-xs); font-weight: 600; color: var(--color-accent); text-transform: uppercase; letter-spacing: 0.04em; }
	.variant-body { margin: 0.25rem 0 0; font-size: var(--text-sm); line-height: 1.5; white-space: pre-wrap; }
	.replies-section { margin-top: 1.25rem; border-top: 1px solid var(--color-border); padding-top: 1rem; }
	.replies-section h3 { margin: 0 0 0.75rem; font-size: 0.95rem; }
	.empty { color: var(--color-text-muted); font-size: var(--text-sm); }
	.compose { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; }
	.compose textarea { padding: 0.5rem; border: 1px solid var(--color-border); border-radius: 4px; font-family: inherit; font-size: var(--text-sm); resize: vertical; }
	.compose button { align-self: flex-end; padding: 0.35rem 0.9rem; background: var(--color-text); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: var(--text-sm); transition: background 0.15s; }
	.compose button:hover:not(:disabled) { background: var(--color-accent); }
	.compose button:disabled { opacity: 0.5; cursor: default; }
</style>
