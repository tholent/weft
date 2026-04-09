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
	import type { Member, MemberRole } from '$lib/types/member';
	import type { Circle } from '$lib/types/circle';
	import { moveMember, promoteMember, renameMember, resendInvite } from '$lib/api/members';
	import { session } from '$lib/stores/session';

	export let member: Member;
	export let circles: Circle[];
	export let viewerRole: MemberRole;

	let selectedCircle = member.circle_id || '';
	let retroactive = false;
	let editingHandle = false;
	let handleInput = member.display_handle || '';

	$: canManage = viewerRole === 'owner' || viewerRole === 'admin';
	$: canPromoteToAdmin = viewerRole === 'owner';

	const roleBadgeStyle: Record<string, string> = {
		creator: 'background: var(--color-accent-light); color: var(--color-accent);',
		admin: 'background: #fef3e2; color: #9a4f08;',
		moderator: 'background: #eff6ff; color: #1d4ed8;',
		recipient: 'background: #f3f4f6; color: #4b5563;'
	};
	$: badgeStyle = roleBadgeStyle[member.role] ?? roleBadgeStyle['recipient'];

	async function handleMove() {
		if (!selectedCircle || !$session.topicId) return;
		await moveMember($session.topicId, member.id, selectedCircle, retroactive);
	}

	async function handlePromote(role: MemberRole) {
		if (!$session.topicId) return;
		await promoteMember($session.topicId, member.id, role);
	}

	async function handleRename() {
		if (!$session.topicId || !handleInput.trim()) return;
		await renameMember($session.topicId, member.id, handleInput.trim());
		member = { ...member, display_handle: handleInput.trim() };
		editingHandle = false;
	}

	async function handleResend() {
		if (!$session.topicId) return;
		await resendInvite($session.topicId, member.id);
	}
</script>

<div class="member-row">
	<div class="info">
		{#if editingHandle}
			<input bind:value={handleInput} on:keydown={(e) => e.key === 'Enter' && handleRename()} />
			<button on:click={handleRename}>Save</button>
			<button on:click={() => (editingHandle = false)}>Cancel</button>
		{:else}
			<span class="handle">{member.display_handle || 'Anonymous'}</span>
			{#if viewerRole === 'owner'}
				<button class="rename-btn" on:click={() => (editingHandle = true)}>✎</button>
			{/if}
		{/if}
		<span class="role-badge" style={badgeStyle}>{member.role}</span>
	</div>

	{#if canManage && member.role !== 'owner'}
		<div class="actions">
			<select bind:value={selectedCircle} on:change={handleMove}>
				<option value="" disabled>Move to...</option>
				{#each circles as c (c.id)}
					<option value={c.id}>{c.name}</option>
				{/each}
			</select>
			<label class="retro"><input type="checkbox" bind:checked={retroactive} /> Retroactive</label>

			{#if member.role === 'recipient'}
				<button class="promote-btn" on:click={() => handlePromote('moderator')}>Make Mod</button>
			{/if}
			{#if canPromoteToAdmin && member.role !== 'admin'}
				<button class="promote-btn" on:click={() => handlePromote('admin')}>Make Admin</button>
			{/if}

			<button class="secondary-btn" on:click={handleResend}>Resend</button>
		</div>
	{/if}
</div>

<style>
	.member-row { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid var(--color-border); flex-wrap: wrap; gap: 0.5rem; }
	.info { display: flex; align-items: center; gap: 0.5rem; }
	.handle { font-weight: 500; }
	.role-badge { padding: 0.1rem 0.5rem; border-radius: 3px; font-size: var(--text-xs); text-transform: capitalize; }
	.actions { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
	select, input { padding: 0.25rem 0.5rem; border: 1px solid var(--color-border); border-radius: 4px; font-size: var(--text-sm); }
	button { padding: 0.25rem 0.6rem; border: 1px solid var(--color-border); border-radius: 4px; font-size: var(--text-sm); cursor: pointer; background: var(--color-surface); color: var(--color-text-secondary); transition: background 0.1s, border-color 0.1s; }
	button:hover { background: var(--color-surface-hover); border-color: var(--color-border-strong); }
	.rename-btn { background: none; border: none; cursor: pointer; padding: 0 0.25rem; color: var(--color-text-secondary); }
	.promote-btn { background: var(--color-accent-light); border-color: #f0d0b0; color: var(--color-accent); font-weight: 500; }
	.promote-btn:hover { background: var(--color-accent); color: white; border-color: var(--color-accent); }
	.secondary-btn { color: var(--color-text-muted); font-size: var(--text-xs); }
	.retro { font-size: var(--text-xs); display: flex; align-items: center; gap: 0.2rem; }
</style>
