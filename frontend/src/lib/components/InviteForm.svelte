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
	import type { Member, MemberRole, NotificationChannel } from '$lib/types/member';
	import { inviteMember } from '$lib/api/members';
	import { session, isOwner } from '$lib/stores/session';

	export let circles: Circle[];
	export let onInvited: (member: Member) => void;

	let email = '';
	let phone = '';
	let displayHandle = '';
	let circleId = '';
	let role: MemberRole = 'recipient';
	let notificationChannel: NotificationChannel = 'email';
	let submitting = false;
	let error = '';
	let success = '';

	$: emailRequired = notificationChannel === 'email';
	$: phoneRequired = notificationChannel === 'sms';
	$: canSubmit = !submitting && !!circleId &&
		(emailRequired ? !!email.trim() : !!phone.trim());

	async function handleSubmit() {
		if (!canSubmit || !$session.topicId) return;
		submitting = true;
		error = '';
		success = '';
		try {
			const member = await inviteMember(
				$session.topicId,
				circleId,
				role,
				displayHandle.trim() || undefined,
				emailRequired ? email.trim() : undefined,
				phoneRequired ? phone.trim() : undefined,
				notificationChannel
			);
			const label = emailRequired ? email.trim() : phone.trim();
			success = `Invite sent to ${label}`;
			email = '';
			phone = '';
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
		<select bind:value={notificationChannel} class="channel-select">
			<option value="email">Email</option>
			<option value="sms">SMS</option>
		</select>
		{#if notificationChannel === 'email'}
			<input
				type="email"
				bind:value={email}
				placeholder="Email address"
				required
			/>
		{/if}
		{#if notificationChannel === 'sms'}
			<input
				type="tel"
				bind:value={phone}
				placeholder="Phone number"
				required
			/>
		{/if}
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
		<button type="submit" disabled={!canSubmit}>
			{submitting ? 'Sending…' : 'Invite'}
		</button>
	</div>
	{#if error}<p class="msg error">{error}</p>{/if}
	{#if success}<p class="msg ok">{success}</p>{/if}
</form>

<style>
	.invite-form { margin-bottom: 1.25rem; }
	.fields { display: flex; gap: 0.5rem; flex-wrap: wrap; }
	input[type="email"], input[type="tel"], input[type="text"] {
		flex: 1; min-width: 180px;
		padding: 0.35rem 0.6rem; border: 1px solid var(--color-border);
		border-radius: 4px; font-size: var(--text-sm);
	}
	.channel-select, select {
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
