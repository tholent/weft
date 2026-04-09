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
	import type { Member } from '$lib/types/member';
	import { session } from '$lib/stores/session';
	import { directTransfer } from '$lib/api/transfer';

	export let members: Member[];
	export let onTransferred: () => void;

	$: candidates = members.filter((m) => m.id !== $session.memberId);

	let selectedId = '';
	let confirming = false;
	let submitting = false;
	let error = '';

	$: selectedMember = candidates.find((m) => m.id === selectedId);

	function handleSelect() {
		if (!selectedId) return;
		confirming = true;
		error = '';
	}

	function handleBack() {
		confirming = false;
	}

	async function handleConfirm() {
		if (!selectedId || !$session.topicId || submitting) return;
		submitting = true;
		error = '';
		try {
			await directTransfer($session.topicId, selectedId);
			onTransferred();
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Transfer failed';
			confirming = false;
		} finally {
			submitting = false;
		}
	}
</script>

<div class="torch">
	{#if !confirming}
		<div class="row">
			<select bind:value={selectedId}>
				<option value="" disabled>Select new owner…</option>
				{#each candidates as m (m.id)}
					<option value={m.id}>{m.display_handle || 'Anonymous'} — {m.role}</option>
				{/each}
			</select>
			<button class="torch-btn" disabled={!selectedId} on:click={handleSelect}>
				Pass the Torch
			</button>
		</div>
	{:else}
		<div class="confirm-box">
			<p class="confirm-msg">
				You are about to transfer ownership to
				<strong>{selectedMember?.display_handle || 'Anonymous'}</strong>.
				You will become an admin. This cannot be undone.
			</p>
			<div class="confirm-actions">
				<button class="confirm-btn" disabled={submitting} on:click={handleConfirm}>
					{submitting ? 'Transferring…' : 'Yes, transfer ownership'}
				</button>
				<button class="cancel-btn" on:click={handleBack}>Cancel</button>
			</div>
		</div>
	{/if}
	{#if error}<p class="error">{error}</p>{/if}
</div>

<style>
	.torch { margin-top: 0.5rem; }
	.row { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
	select {
		padding: 0.35rem 0.5rem; border: 1px solid var(--color-border);
		border-radius: 4px; font-size: var(--text-sm);
		background: var(--color-surface); color: var(--color-text); flex: 1; min-width: 180px;
	}
	.torch-btn {
		padding: 0.35rem 1rem; border: none; border-radius: 4px;
		background: var(--color-text); color: white;
		font-size: var(--text-sm); cursor: pointer; transition: background 0.15s; white-space: nowrap;
	}
	.torch-btn:hover:not(:disabled) { background: var(--color-accent); }
	.torch-btn:disabled { opacity: 0.4; cursor: default; }
	.confirm-box {
		background: #fff8f0; border: 1px solid #f0d0b0;
		border-left: 4px solid var(--color-accent);
		border-radius: 4px; padding: 0.75rem 1rem;
	}
	.confirm-msg { margin: 0 0 0.75rem; font-size: var(--text-sm); line-height: 1.5; }
	.confirm-actions { display: flex; gap: 0.5rem; }
	.confirm-btn {
		padding: 0.35rem 1rem; border: none; border-radius: 4px;
		background: var(--color-accent); color: white;
		font-size: var(--text-sm); cursor: pointer; transition: background 0.15s;
	}
	.confirm-btn:hover:not(:disabled) { background: #a0500a; }
	.confirm-btn:disabled { opacity: 0.5; cursor: default; }
	.cancel-btn {
		padding: 0.35rem 0.8rem; border: 1px solid var(--color-border);
		border-radius: 4px; background: var(--color-surface);
		color: var(--color-text-secondary); font-size: var(--text-sm); cursor: pointer;
	}
	.error { color: var(--color-danger); font-size: var(--text-sm); margin: 0.4rem 0 0; }
</style>
