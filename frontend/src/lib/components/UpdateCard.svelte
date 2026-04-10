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
	import type { Update } from '$lib/types/update';
	import type { Circle } from '$lib/types/circle';
	import { getAttachmentUrl } from '$lib/api/attachments';

	export let update: Update;
	export let topicId: string = '';
	export let circles: Circle[] = [];
	export let onClick: (() => void) | undefined = undefined;
	export let canReply: boolean = false;
	export let canEdit: boolean = false;
	export let canDelete: boolean = false;

	$: preview = update.deleted_at ? '[removed]' : update.body;

	$: circleEntries = update.circle_ids
		.map((id) => ({ name: circles.find((c) => c.id === id)?.name, hasVariant: id in update.body_variants }))
		.filter((e): e is { name: string; hasVariant: boolean } => e.name !== undefined);

	$: attachments = update.attachments ?? [];

	let lightboxSrc: string | null = null;

	function openLightbox(src: string, e: MouseEvent) {
		e.stopPropagation();
		lightboxSrc = src;
	}

	function closeLightbox() {
		lightboxSrc = null;
	}
</script>

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
<div class="update-row" class:deleted={!!update.deleted_at} on:click={onClick ?? (() => {})}>
	<p class="preview">{preview}</p>

	{#if attachments.length > 0 && !update.deleted_at}
		<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
		<div class="attachment-grid" on:click|stopPropagation>
			{#each attachments as attachment (attachment.id)}
				{@const src = getAttachmentUrl(topicId, attachment.id)}
				<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
				<button type="button" class="thumb-btn" on:click={(e) => openLightbox(src, e)}>
					<img class="thumb" {src} alt={attachment.filename} loading="lazy" />
				</button>
			{/each}
		</div>
	{/if}

	<div class="row-footer">
		<div class="meta">
			<span>{update.author_handle || 'Anonymous'}</span>
			<span>{new Date(update.created_at).toLocaleString()}</span>
			{#if update.edited_at}<span class="edited">(edited)</span>{/if}
		</div>
		<div class="right">
			{#each circleEntries as entry}
				<span class="pill" class:pill-variant={entry.hasVariant}>
					{entry.name}{#if entry.hasVariant}<span class="pill-alt">ALT</span>{/if}
				</span>
			{/each}
			{#if update.pending_reply_count > 0}
				<span class="pending-badge" title="Awaiting moderation">{update.pending_reply_count} pending</span>
			{/if}
			{#if update.reply_count > 0}
				<span class="reply-badge">{update.reply_count} {update.reply_count === 1 ? 'reply' : 'replies'}</span>
			{/if}
		</div>
	</div>
</div>

{#if lightboxSrc}
	<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
	<div class="lightbox-overlay" on:click={closeLightbox}>
		<img class="lightbox-img" src={lightboxSrc} alt="Full size" />
	</div>
{/if}

<style>
	.update-row {
		border: 1px solid var(--color-border); border-left: 3px solid var(--color-border);
		border-radius: 8px; padding: 0.75rem 1rem; margin: 0.5rem 0;
		cursor: pointer; transition: background 0.15s, box-shadow 0.15s, border-left-color 0.15s;
	}
	.update-row:hover {
		background: var(--color-surface-hover);
		box-shadow: 0 1px 4px rgba(0,0,0,0.07);
		border-left-color: var(--color-accent);
	}
	.update-row.deleted { opacity: 0.5; }
	.preview {
		margin: 0 0 0.5rem; line-height: 1.6;
		font-family: var(--font-display); font-size: var(--text-base);
		display: -webkit-box;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.attachment-grid {
		display: flex; flex-wrap: wrap; gap: 0.4rem;
		margin-bottom: 0.5rem;
	}
	.thumb-btn {
		padding: 0; border: none; background: none; cursor: pointer;
		border-radius: 4px; overflow: hidden;
		border: 1px solid var(--color-border);
	}
	.thumb {
		display: block; width: 80px; height: 80px; object-fit: cover;
		transition: opacity 0.15s;
	}
	.thumb-btn:hover .thumb { opacity: 0.85; }

	.lightbox-overlay {
		position: fixed; inset: 0; background: rgba(0,0,0,0.8);
		display: flex; align-items: center; justify-content: center;
		z-index: 1000; cursor: zoom-out;
	}
	.lightbox-img {
		max-width: 90vw; max-height: 90vh;
		object-fit: contain; border-radius: 4px;
	}

	.row-footer { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; }
	.meta { font-size: var(--text-sm); color: var(--color-text-secondary); display: flex; gap: 0.5rem; flex-wrap: wrap; }
	.edited { font-style: italic; }
	.right { display: flex; gap: 0.25rem; align-items: center; flex-wrap: wrap; }
	.pill {
		font-size: var(--text-xs); background: var(--color-accent-light);
		border-radius: 4px; padding: 0.1rem 0.6rem;
		color: var(--color-accent); border: 1px solid #f0d0b0;
		display: inline-flex; align-items: stretch; gap: 0;
	}
	.pill-variant { padding-right: 0; overflow: hidden; }
	.pill-alt {
		display: inline-flex; align-items: center; align-self: stretch;
		background: var(--color-accent); color: white;
		font-size: 0.55rem; font-weight: 700; letter-spacing: 0.06em;
		padding: 0 0.35rem; margin-left: 0.4rem;
		margin-top: -0.1rem; margin-bottom: -0.1rem;
		border-radius: 0 3px 3px 0;
	}
	.pending-badge {
		font-size: var(--text-xs); color: #92400e;
		background: #fef3c7; border: 1px solid #fcd34d;
		border-radius: 4px; padding: 0.1rem 0.5rem; font-weight: 500;
	}
	.reply-badge {
		font-size: var(--text-xs); color: var(--color-text-secondary);
		background: var(--color-surface-hover); border: 1px solid var(--color-border);
		border-radius: 4px; padding: 0.1rem 0.5rem;
	}
</style>
