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
	import { circles } from '$lib/stores/topic';
	import { session } from '$lib/stores/session';
	import { createCircle, renameCircle, deleteCircle, listCircles } from '$lib/api/circles';

	let newName = '';
	let newScopedTitle = '';
	let editingId: string | null = null;
	let editName = '';
	let editScopedTitle = '';

	async function handleCreate() {
		if (!newName.trim() || !$session.topicId) return;
		await createCircle($session.topicId, newName, newScopedTitle || undefined);
		circles.set(await listCircles($session.topicId));
		newName = '';
		newScopedTitle = '';
	}

	function startEdit(circle: { id: string; name: string; scoped_title: string | null }) {
		editingId = circle.id;
		editName = circle.name;
		editScopedTitle = circle.scoped_title || '';
	}

	async function handleRename() {
		if (!editingId || !$session.topicId) return;
		await renameCircle($session.topicId, editingId, editName, editScopedTitle || undefined);
		circles.set(await listCircles($session.topicId));
		editingId = null;
	}

	async function handleDelete(circleId: string) {
		if (!$session.topicId || !confirm('Delete this circle?')) return;
		try {
			await deleteCircle($session.topicId, circleId);
			circles.set(await listCircles($session.topicId));
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Cannot delete circle');
		}
	}
</script>

<section>
	<h2>Circles</h2>
	{#each $circles as circle (circle.id)}
		<div class="circle-row">
			{#if editingId === circle.id}
				<input bind:value={editName} placeholder="Name" />
				<input bind:value={editScopedTitle} placeholder="Scoped title (optional)" />
				<button on:click={handleRename}>Save</button>
				<button on:click={() => (editingId = null)}>Cancel</button>
			{:else}
				<strong>{circle.name}</strong>
				{#if circle.scoped_title}<span class="scoped">({circle.scoped_title})</span>{/if}
				<button on:click={() => startEdit(circle)}>Edit</button>
				<button class="danger" on:click={() => handleDelete(circle.id)}>Delete</button>
			{/if}
		</div>
	{/each}

	<form class="create-form" on:submit|preventDefault={handleCreate}>
		<input bind:value={newName} placeholder="New circle name" />
		<input bind:value={newScopedTitle} placeholder="Scoped title (optional)" />
		<button type="submit">Add Circle</button>
	</form>
</section>

<style>
	.circle-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0;
		border-bottom: 1px solid var(--color-border);
	}
	.scoped {
		color: var(--color-text-secondary);
		font-size: var(--text-sm);
	}
	.create-form {
		display: flex;
		gap: 0.5rem;
		margin-top: 1rem;
	}
	input {
		padding: 0.4rem;
		border: 1px solid var(--color-border);
		border-radius: 4px;
	}
	button {
		padding: 0.3rem 0.75rem;
		border: 1px solid var(--color-border);
		border-radius: 4px;
		cursor: pointer;
		background: var(--color-surface);
	}
	button:hover {
		background: var(--color-surface-hover);
	}
	.danger {
		color: var(--color-danger);
		border-color: var(--color-danger);
	}
</style>
