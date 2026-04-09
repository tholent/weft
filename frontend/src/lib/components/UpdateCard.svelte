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

	export let update: Update;
	export let canReply: boolean;
	export let canEdit: boolean;
	export let canDelete: boolean;
</script>

<article class="update-card">
	{#if update.deleted_at}
		<p class="deleted">[This update has been removed]</p>
	{:else}
		<p class="body">{update.body}</p>
		<div class="meta">
			<span>{update.author_handle || 'Anonymous'}</span>
			<span>{new Date(update.created_at).toLocaleString()}</span>
			{#if update.edited_at}<span class="edited">(edited)</span>{/if}
		</div>
		{#if update.circle_ids.length > 0}
			<div class="circles">Circles: {update.circle_ids.length}</div>
		{/if}
	{/if}
</article>

<style>
	.update-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin: 0.75rem 0; }
	.body { margin: 0 0 0.5rem; line-height: 1.5; }
	.meta { font-size: 0.85rem; color: #666; display: flex; gap: 0.75rem; }
	.edited { font-style: italic; }
	.deleted { color: #999; font-style: italic; }
	.circles { font-size: 0.8rem; color: #888; margin-top: 0.25rem; }
</style>
