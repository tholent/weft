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
	import { onMount } from 'svelte';
	import { session, isModerator, isAdmin, isOwner, login } from '$lib/stores/session';
	import { topic, updates, circles, members } from '$lib/stores/topic';
	import { getTopic, closeTopic } from '$lib/api/topics';
	import { getFeed, createUpdate } from '$lib/api/updates';
	import { listCircles } from '$lib/api/circles';
	import { listMembers } from '$lib/api/members';
	import UpdateCard from '$lib/components/UpdateCard.svelte';
	import UpdateModal from '$lib/components/UpdateModal.svelte';
	import ComposeBox from '$lib/components/ComposeBox.svelte';
	import CircleManager from '$lib/components/CircleManager.svelte';
	import MemberRow from '$lib/components/MemberRow.svelte';
	import InviteForm from '$lib/components/InviteForm.svelte';
	import TransferBanner from '$lib/components/TransferBanner.svelte';
	import PassTheTorch from '$lib/components/PassTheTorch.svelte';
	import NotificationSettings from '$lib/components/NotificationSettings.svelte';
	import ExportButton from '$lib/components/ExportButton.svelte';
	import type { Update } from '$lib/types/update';
	import type { Member } from '$lib/types/member';

	let activeTab: 'updates' | 'members' | 'circles' | 'settings' = 'updates';
	let loading = true;
	let selectedUpdate: Update | null = null;

	type SortKey = 'newest' | 'oldest' | 'most_replies';
	let sortKey: SortKey = 'newest';
	let filterCircleIds: string[] = [];
	let showDeleted = false;
	let circlePopoverOpen = false;

	$: filteredUpdates = $updates
		.filter((u) => showDeleted || !u.deleted_at)
		.filter((u) => filterCircleIds.length === 0 || u.circle_ids.some((id) => filterCircleIds.includes(id)))
		.sort((a, b) => {
			if (sortKey === 'newest') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
			if (sortKey === 'oldest') return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
			return b.reply_count - a.reply_count;
		});

	function toggleFilterCircle(id: string) {
		filterCircleIds = filterCircleIds.includes(id)
			? filterCircleIds.filter((c) => c !== id)
			: [...filterCircleIds, id];
	}

	function handleWindowClick(e: MouseEvent) {
		if (circlePopoverOpen && !(e.target as Element).closest('.circle-filter-wrap')) {
			circlePopoverOpen = false;
		}
	}

	onMount(async () => {
		if (!$session.topicId) return;
		try {
			const [t, feed, c, m] = await Promise.all([
				getTopic($session.topicId),
				getFeed($session.topicId),
				listCircles($session.topicId),
				listMembers($session.topicId)
			]);
			topic.set(t);
			updates.set(feed);
			circles.set(c);
			members.set(m);
		} finally {
			loading = false;
		}
	});

	async function handleNewUpdate(data: Record<string, unknown>): Promise<{ id: string }> {
		if (!$session.topicId) return { id: '' };
		const update = await createUpdate(
			$session.topicId,
			data.body as string,
			data.circle_ids as string[],
			(data.circle_bodies as Record<string, string>) ?? {}
		);
		updates.set(await getFeed($session.topicId));
		return update;
	}

	async function handleClose() {
		if (!$session.topicId || !confirm('Close this topic? All emails will be purged.')) return;
		await closeTopic($session.topicId);
		topic.set(await getTopic($session.topicId));
	}
</script>

<svelte:window on:click={handleWindowClick} />

<main>
	{#if loading}
		<p>Loading...</p>
	{:else if $topic}
		<h1>{$topic.default_title}</h1>

		<nav>
			<button class:active={activeTab === 'updates'} on:click={() => (activeTab = 'updates')}>Updates</button>
			<button class:active={activeTab === 'members'} on:click={() => (activeTab = 'members')}>Members</button>
			{#if $isAdmin}
				<button class:active={activeTab === 'circles'} on:click={() => (activeTab = 'circles')}>Circles</button>
				<button class:active={activeTab === 'settings'} on:click={() => (activeTab = 'settings')}>Settings</button>
			{/if}
		</nav>

		{#if activeTab === 'updates'}
			{#if $isModerator}
				<p class="section-label">Post Update</p>
				<ComposeBox mode="update" targetCircles={$circles} onSubmit={handleNewUpdate} />
				<hr />
			{/if}
			<div class="list-controls">
				<div class="controls-left">
					{#if $circles.length > 0}
						<div class="circle-filter-wrap">
							<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
							<button
								class="circle-filter-btn"
								class:active={filterCircleIds.length > 0}
								on:click|stopPropagation={() => (circlePopoverOpen = !circlePopoverOpen)}
							>
								Circles{filterCircleIds.length > 0 ? ` (${filterCircleIds.length})` : ''}
							</button>
							{#if circlePopoverOpen}
								<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
								<div class="circle-popover" on:click|stopPropagation>
									{#if filterCircleIds.length > 0}
										<button class="clear-btn" on:click={() => (filterCircleIds = [])}>Clear all</button>
									{/if}
									{#each $circles as circle (circle.id)}
										{@const selected = filterCircleIds.includes(circle.id)}
										<button
											class="popover-pill"
											class:selected
											on:click={() => toggleFilterCircle(circle.id)}
										>{circle.name}</button>
									{/each}
								</div>
							{/if}
						</div>
					{/if}
				</div>
				<div class="controls-right">
					{#if $updates.some((u) => u.deleted_at)}
						<label class="deleted-toggle">
							<input type="checkbox" bind:checked={showDeleted} />
							Show removed
						</label>
					{/if}
					<select bind:value={sortKey} class="sort-select">
						<option value="newest">Newest</option>
						<option value="oldest">Oldest</option>
						<option value="most_replies">Most replies</option>
					</select>
				</div>
			</div>
			{#each filteredUpdates as update (update.id)}
				<UpdateCard {update} topicId={$session.topicId ?? ''} circles={$circles} onClick={() => (selectedUpdate = update)} />
			{/each}
			{#if filteredUpdates.length === 0}
				<p class="empty-list">No updates match the current filter.</p>
			{/if}
		{:else if activeTab === 'members'}
			<h2>Members</h2>
			{#if $isAdmin}
				<p class="section-label">Invite</p>
				<InviteForm
					circles={$circles}
					onInvited={(m: Member) => members.update((all) => [...all, m])}
				/>
				<hr />
			{/if}
			{#each $members as member (member.id)}
				<MemberRow {member} circles={$circles} viewerRole={$session.role || 'recipient'} />
			{/each}
		{:else if activeTab === 'circles'}
			<CircleManager />
		{:else if activeTab === 'settings'}
			<h2>Settings</h2>
			<TransferBanner />

			<p class="section-label">Notification Settings</p>
			<NotificationSettings />
			<hr />

			{#if $isAdmin && $session.topicId}
				<p class="section-label">Export</p>
				<ExportButton topicId={$session.topicId} />
				<hr />
			{/if}

			{#if $isOwner}
				<p class="section-label">Pass the Torch</p>
				<PassTheTorch
					members={$members}
					onTransferred={() => {
						if ($session.token && $session.memberId && $session.topicId)
							login($session.token, $session.memberId, 'admin', $session.topicId);
					}}
				/>
				<hr />
				<button class="danger" on:click={handleClose}>Close Topic</button>
			{/if}
		{/if}
	{/if}
</main>

{#if selectedUpdate && $session.topicId}
	<UpdateModal
		update={selectedUpdate}
		circles={$circles}
		isModerator={$isModerator}
		canEdit={selectedUpdate.author_member_id === $session.memberId}
		topicId={$session.topicId}
		onClose={() => (selectedUpdate = null)}
		onUpdate={(updated) => updates.update((all) => all.map((u) => (u.id === updated.id ? updated : u)))}
	/>
{/if}

<style>
	main { max-width: var(--content-width); margin: 2rem auto; padding: 0 1rem; }
	h1 { padding-bottom: 1rem; border-bottom: 1px solid var(--color-border); margin-bottom: 1.5rem; }
	nav { display: flex; gap: 0.5rem; margin: 1rem 0; border-bottom: 1px solid var(--color-border); padding-bottom: 0.5rem; }
	nav button {
		background: none; border: none; border-bottom: 2px solid transparent;
		padding: 0.5rem 1rem; cursor: pointer; border-radius: 0;
		letter-spacing: 0.03em; text-transform: uppercase; font-size: var(--text-xs);
		color: var(--color-text-secondary);
		margin-bottom: -1px;
	}
	nav button.active { border-bottom-color: var(--color-accent); color: var(--color-accent); }
	.section-label {
		font-size: var(--text-xs); font-weight: 600; letter-spacing: 0.08em;
		text-transform: uppercase; color: var(--color-text-muted);
		margin: 0 0 0.5rem;
	}
	hr { border: none; border-top: 1px solid var(--color-border); margin: 1.25rem 0; }
	.list-controls {
		display: flex; justify-content: space-between; align-items: center;
		flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.75rem;
	}
	.controls-left { display: flex; gap: 0.25rem; flex-wrap: wrap; align-items: center; flex: 1; }
	.controls-right { display: flex; gap: 0.5rem; align-items: center; flex-shrink: 0; }
	.circle-filter-wrap { position: relative; }
	.circle-filter-btn {
		padding: 0.2rem 0.65rem; border-radius: 4px; font-size: var(--text-xs);
		border: 1px solid var(--color-border-strong); background: none;
		color: var(--color-text-secondary); cursor: pointer; transition: all 0.1s;
	}
	.circle-filter-btn.active {
		background: var(--color-accent-light); border-color: var(--color-accent);
		color: var(--color-accent);
	}
	.circle-popover {
		position: absolute; top: calc(100% + 0.35rem); left: 0;
		background: var(--color-surface); border: 1px solid var(--color-border);
		border-radius: 6px; padding: 0.5rem; z-index: 50;
		display: flex; flex-direction: column; gap: 0.3rem;
		box-shadow: 0 4px 12px rgba(0,0,0,0.1); min-width: 150px;
	}
	.popover-pill {
		padding: 0.2rem 0.65rem; border-radius: 4px; font-size: var(--text-xs);
		border: 1px solid var(--color-border-strong); background: none;
		color: var(--color-text-secondary); cursor: pointer; transition: all 0.1s;
		text-align: left;
	}
	.popover-pill.selected {
		background: var(--color-accent-light); border-color: var(--color-accent);
		color: var(--color-accent);
	}
	.clear-btn {
		font-size: var(--text-xs); color: var(--color-text-muted); background: none;
		border: none; cursor: pointer; padding: 0 0.25rem 0.25rem;
		text-align: left; border-bottom: 1px solid var(--color-border); margin-bottom: 0.1rem;
	}
	.clear-btn:hover { color: var(--color-accent); }
	.sort-select {
		padding: 0.2rem 0.4rem; border: 1px solid var(--color-border);
		border-radius: 4px; font-size: var(--text-xs); background: var(--color-surface);
		color: var(--color-text-secondary);
	}
	.deleted-toggle {
		display: flex; align-items: center; gap: 0.25rem;
		font-size: var(--text-xs); color: var(--color-text-muted); cursor: pointer;
	}
	.empty-list { color: var(--color-text-muted); font-size: var(--text-sm); text-align: center; padding: 2rem 0; }
	.danger { background: var(--color-danger); color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; margin-top: 1rem; }
</style>
