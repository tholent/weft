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

	export let update: Update;
	export let circles: Circle[] = [];
	export let onClick: () => void;

	$: preview = update.deleted_at ? '[removed]' : update.body;

	$: circleNames = update.circle_ids
		.map((id) => circles.find((c) => c.id === id)?.name)
		.filter((name): name is string => name !== undefined);
</script>

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
<div class="update-row" class:deleted={!!update.deleted_at} on:click={onClick}>
	<p class="preview">{preview}</p>
	<div class="row-footer">
		<div class="meta">
			<span>{update.author_handle || 'Anonymous'}</span>
			<span>{new Date(update.created_at).toLocaleString()}</span>
			{#if update.edited_at}<span class="edited">(edited)</span>{/if}
		</div>
		<div class="right">
			{#each circleNames as name}
				<span class="pill">{name}</span>
			{/each}
			{#if update.reply_count > 0}
				<span class="reply-count">{update.reply_count} {update.reply_count === 1 ? 'reply' : 'replies'}</span>
			{/if}
		</div>
	</div>
</div>

<style>
	.update-row {
		border: 1px solid var(--color-border); border-radius: 8px;
		padding: 0.75rem 1rem; margin: 0.5rem 0;
		cursor: pointer; transition: background 0.1s, box-shadow 0.1s;
	}
	.update-row:hover { background: var(--color-surface-hover); box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
	.update-row.deleted { opacity: 0.5; }
	.preview {
		margin: 0 0 0.5rem; line-height: 1.5;
		display: -webkit-box;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.row-footer { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; }
	.meta { font-size: var(--text-sm); color: var(--color-text-secondary); display: flex; gap: 0.5rem; flex-wrap: wrap; }
	.edited { font-style: italic; }
	.right { display: flex; gap: 0.25rem; align-items: center; flex-wrap: wrap; }
	.pill { font-size: var(--text-xs); background: var(--color-accent-light); border-radius: 999px; padding: 0.1rem 0.6rem; color: var(--color-accent); border: 1px solid #f0d0b0; }
	.reply-count { font-size: var(--text-xs); color: var(--color-text-muted); }
</style>
