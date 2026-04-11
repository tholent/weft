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
	import type { Reply } from '$lib/types/reply';

	export let replies: Reply[];
	export let isModerator: boolean;
	export let onRelay: ((replyId: string) => Promise<void>) | null = null;
	export let onDismiss: ((replyId: string) => Promise<void>) | null = null;

	let actioning: string | null = null;

	async function relay(replyId: string) {
		if (!onRelay || actioning) return;
		actioning = replyId;
		try {
			await onRelay(replyId);
		} finally {
			actioning = null;
		}
	}

	async function dismiss(replyId: string) {
		if (!onDismiss || actioning) return;
		actioning = replyId;
		try {
			await onDismiss(replyId);
		} finally {
			actioning = null;
		}
	}
</script>

<div class="reply-thread">
	{#each replies as reply (reply.id)}
		<div class="reply" class:pending={isModerator && reply.relay_status === 'pending'}>
			<p class="reply-body">{reply.body}</p>
			<div class="reply-meta">
				<span>{reply.author_handle || 'Anonymous'}</span>
				<span>{new Date(reply.created_at).toLocaleString()}</span>
				{#if reply.wants_to_share}<span class="badge">Shared</span>{/if}
				{#if isModerator}
					{#if reply.relay_status === 'pending'}
						<button
							class="action approve"
							disabled={actioning === reply.id}
							on:click={() => relay(reply.id)}>Approve</button
						>
						<button
							class="action dismiss"
							disabled={actioning === reply.id}
							on:click={() => dismiss(reply.id)}>Dismiss</button
						>
					{:else}
						<span class="badge status {reply.relay_status}">{reply.relay_status}</span>
						{#if reply.relay_status === 'dismissed'}
							<button
								class="action undo"
								disabled={actioning === reply.id}
								on:click={() => relay(reply.id)}>Undo</button
							>
						{/if}
					{/if}
				{/if}
			</div>
			{#if reply.mod_responses.length > 0}
				<div class="mod-responses">
					{#each reply.mod_responses as mr (mr.id)}
						<div class="mod-response">
							<p>{mr.body}</p>
							<span class="mod-meta">{mr.author_handle || 'Moderator'} · {mr.scope}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/each}
</div>

<style>
	.reply-thread {
		margin-left: 1rem;
		border-left: 3px solid var(--color-border-strong);
		padding-left: 1rem;
	}
	.reply {
		margin: 0.5rem 0;
		padding: 0.5rem 0;
	}
	.reply.pending {
		background: #fffbeb;
		border-radius: 4px;
		padding: 0.5rem;
		margin-left: -0.5rem;
	}
	.reply-body {
		margin: 0 0 0.25rem;
	}
	.reply-meta {
		font-size: var(--text-xs);
		color: var(--color-text-secondary);
		display: flex;
		gap: 0.5rem;
		align-items: center;
		flex-wrap: wrap;
	}
	.badge {
		background: var(--color-border);
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		font-size: var(--text-xs);
	}
	.badge.status {
		text-transform: capitalize;
	}
	.badge.pending {
		background: #fef3c7;
		color: #92400e;
		border: 1px solid #fcd34d;
	}
	.badge.relayed {
		background: #d1fae5;
		color: #065f46;
		border: 1px solid #6ee7b7;
	}
	.badge.dismissed {
		background: var(--color-border);
		color: var(--color-text-muted);
	}
	.action {
		font-size: var(--text-xs);
		padding: 0.1rem 0.5rem;
		border-radius: 3px;
		cursor: pointer;
		border: 1px solid;
		transition: all 0.1s;
	}
	.action:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.action.approve {
		background: #d1fae5;
		color: #065f46;
		border-color: #6ee7b7;
	}
	.action.approve:hover:not(:disabled) {
		background: #065f46;
		color: white;
	}
	.action.dismiss {
		background: none;
		color: var(--color-text-secondary);
		border-color: var(--color-border-strong);
	}
	.action.dismiss:hover:not(:disabled) {
		background: var(--color-border);
	}
	.action.undo {
		background: none;
		color: var(--color-text-muted);
		border-color: var(--color-border);
		font-style: italic;
	}
	.action.undo:hover:not(:disabled) {
		color: var(--color-text-secondary);
		border-color: var(--color-border-strong);
	}
	.mod-responses {
		margin-left: 1rem;
		margin-top: 0.5rem;
	}
	.mod-response {
		background: var(--color-accent-light);
		padding: 0.5rem;
		border-radius: 4px;
		margin: 0.25rem 0;
	}
	.mod-response p {
		margin: 0 0 0.25rem;
	}
	.mod-meta {
		font-size: var(--text-xs);
		color: var(--color-accent);
	}
</style>
