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
	import type { Circle } from '$lib/types/circle';

	export let mode: 'update' | 'reply' | 'mod_response';
	export let targetCircles: Circle[] = [];
	export let onSubmit: (data: Record<string, unknown>) => void;

	let body = '';
	let selectedCircles: string[] = [];
	let wantsToShare = false;
	let scope: 'sender_only' | 'sender_circle' | 'all_circles' = 'sender_only';

	function handleSubmit() {
		if (!body.trim()) return;
		if (mode === 'update') {
			onSubmit({ body, circle_ids: selectedCircles });
		} else if (mode === 'reply') {
			onSubmit({ body, wants_to_share: wantsToShare });
		} else {
			onSubmit({ body, scope });
		}
		body = '';
	}
</script>

<form class="compose" on:submit|preventDefault={handleSubmit}>
	{#if mode === 'update' && targetCircles.length > 0}
		<div class="circle-select">
			{#each targetCircles as circle (circle.id)}
				<label class="circle-check">
					<input type="checkbox" value={circle.id} bind:group={selectedCircles} />
					{circle.name}
				</label>
			{/each}
		</div>
	{/if}

	<textarea bind:value={body} placeholder={mode === 'update' ? 'Write an update...' : mode === 'reply' ? 'Write a reply...' : 'Write a response...'} rows="3"></textarea>

	{#if mode === 'reply'}
		<label class="share-check">
			<input type="checkbox" bind:checked={wantsToShare} />
			Share with group
		</label>
	{/if}

	{#if mode === 'mod_response'}
		<select bind:value={scope}>
			<option value="sender_only">Sender only</option>
			<option value="sender_circle">Sender's circle</option>
			<option value="all_circles">All circles</option>
		</select>
	{/if}

	<button type="submit">Send</button>
</form>

<style>
	.compose { display: flex; flex-direction: column; gap: 0.5rem; margin: 0.5rem 0; }
	textarea { padding: 0.5rem; border: 1px solid var(--color-border); border-radius: 4px; font-family: inherit; resize: vertical; }
	.circle-select { display: flex; gap: 0.75rem; flex-wrap: wrap; }
	.circle-check, .share-check { display: flex; align-items: center; gap: 0.25rem; font-size: var(--text-sm); }
	select { padding: 0.4rem; border: 1px solid var(--color-border); border-radius: 4px; }
	button { align-self: flex-start; padding: 0.4rem 1rem; background: var(--color-text); color: white; border: none; border-radius: 4px; cursor: pointer; transition: background 0.15s; }
	button:hover { background: var(--color-accent); }
</style>
