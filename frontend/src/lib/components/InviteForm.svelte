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
	import type { Member, MemberRole } from '$lib/types/member';
	import { inviteMember } from '$lib/api/members';
	import { session, isOwner } from '$lib/stores/session';

	export let circles: Circle[];
	export let onInvited: (member: Member) => void;

	let email = '';
	let displayHandle = '';
	let circleId = '';
	let role: MemberRole = 'recipient';
	let submitting = false;
	let error = '';
	let success = '';

	async function handleSubmit() {
		if (!email.trim() || !circleId || !$session.topicId) return;
		submitting = true;
		error = '';
		success = '';
		try {
			const member = await inviteMember($session.topicId, email.trim(), circleId, role, displayHandle.trim() || undefined);
			success = `Invite sent to ${email.trim()}`;
			email = '';
			displayHandle = '';
			onInvited(member);
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Failed to send invite';
		} finally {
			submitting = false;
		}
	}
</script>

<form class="invite-form" on:submit|preventDefault={handleSubmit}>
	<div class="fields">
		<input
			type="email"
			bind:value={email}
			placeholder="Email address"
			required
		/>
		<input
			type="text"
			bind:value={displayHandle}
			placeholder="Name (optional)"
		/>
		<select bind:value={circleId} required>
			<option value="" disabled>Circle…</option>
			{#each circles as circle (circle.id)}
				<option value={circle.id}>{circle.name}</option>
			{/each}
		</select>
		<select bind:value={role}>
			<option value="recipient">Recipient</option>
			<option value="moderator">Moderator</option>
			{#if $isOwner}<option value="admin">Admin</option>{/if}
		</select>
		<button type="submit" disabled={submitting || !email.trim() || !circleId}>
			{submitting ? 'Sending…' : 'Invite'}
		</button>
	</div>
	{#if error}<p class="msg error">{error}</p>{/if}
	{#if success}<p class="msg ok">{success}</p>{/if}
</form>

<style>
	.invite-form { margin-bottom: 1.25rem; }
	.fields { display: flex; gap: 0.5rem; flex-wrap: wrap; }
	input[type="email"], input[type="text"] {
		flex: 1; min-width: 180px;
		padding: 0.35rem 0.6rem; border: 1px solid var(--color-border);
		border-radius: 4px; font-size: var(--text-sm);
	}
	select {
		padding: 0.35rem 0.5rem; border: 1px solid var(--color-border);
		border-radius: 4px; font-size: var(--text-sm);
		background: var(--color-surface); color: var(--color-text);
	}
	button {
		padding: 0.35rem 1rem; background: var(--color-text); color: white;
		border: none; border-radius: 4px; font-size: var(--text-sm);
		cursor: pointer; transition: background 0.15s; white-space: nowrap;
	}
	button:hover:not(:disabled) { background: var(--color-accent); }
	button:disabled { opacity: 0.5; cursor: default; }
	.msg { font-size: var(--text-sm); margin: 0.4rem 0 0; }
	.error { color: var(--color-danger); }
	.ok { color: #166534; }
</style>
