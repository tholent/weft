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
		.filter(
			(u) => filterCircleIds.length === 0 || u.circle_ids.some((id) => filterCircleIds.includes(id))
		)
		.sort((a, b) => {
			if (sortKey === 'newest')
				return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
			if (sortKey === 'oldest')
				return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
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

{#if loading}
	<div class="topic-header topic-header--skeleton">
		<div class="header-inner">
			<div class="skeleton-line" style="width: 50%; height: 2.4rem; border-radius: 3px;"></div>
			<div
				class="skeleton-line"
				style="width: 20%; height: 0.7rem; margin-top: 0.75rem; border-radius: 3px;"
			></div>
		</div>
	</div>
	<div class="content-wrapper">
		<div class="skeleton-nav">
			{#each Array(4) as _}
				<div class="skeleton-line" style="width: 4.5rem; height: 1rem; border-radius: 3px;"></div>
			{/each}
		</div>
		{#each Array(4) as _}
			<div class="skeleton-card">
				<div class="skeleton-line" style="width: 88%"></div>
				<div class="skeleton-line" style="width: 72%"></div>
				<div class="skeleton-line" style="width: 55%"></div>
				<div class="skeleton-meta"></div>
			</div>
		{/each}
	</div>
{:else if $topic}
	<div class="topic-header">
		<div class="header-inner">
			<h1>{$topic.default_title}</h1>
			<p class="header-meta">
				<span class="role-badge">{$session.role}</span>
			</p>
		</div>
	</div>

	<div class="content-wrapper">
		<nav>
			<button class:active={activeTab === 'updates'} on:click={() => (activeTab = 'updates')}
				>Updates</button
			>
			<button class:active={activeTab === 'members'} on:click={() => (activeTab = 'members')}
				>Members</button
			>
			{#if $isAdmin}
				<button class:active={activeTab === 'circles'} on:click={() => (activeTab = 'circles')}
					>Circles</button
				>
				<button class:active={activeTab === 'settings'} on:click={() => (activeTab = 'settings')}
					>Settings</button
				>
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
										<button class="clear-btn" on:click={() => (filterCircleIds = [])}
											>Clear all</button
										>
									{/if}
									{#each $circles as circle (circle.id)}
										{@const selected = filterCircleIds.includes(circle.id)}
										<button
											class="popover-pill"
											class:selected
											on:click={() => toggleFilterCircle(circle.id)}>{circle.name}</button
										>
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
				<UpdateCard
					{update}
					topicId={$session.topicId ?? ''}
					circles={$circles}
					onClick={() => (selectedUpdate = update)}
				/>
			{/each}
			{#if filteredUpdates.length === 0}
				<div class="empty-state">
					<p class="empty-headline">
						{filterCircleIds.length > 0 ? 'No updates in this circle.' : 'Nothing posted yet.'}
					</p>
					<p class="empty-body">
						{filterCircleIds.length > 0
							? 'Try removing the circle filter to see all updates.'
							: $isModerator
								? 'Use the form above to post your first update.'
								: 'Updates will appear here once they are posted.'}
					</p>
				</div>
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
			{#if $members.length === 0}
				<div class="empty-state">
					<p class="empty-headline">No members yet.</p>
					<p class="empty-body">Invite people above to get started.</p>
				</div>
			{/if}
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
	</div>
{/if}

{#if selectedUpdate && $session.topicId}
	<UpdateModal
		update={selectedUpdate}
		circles={$circles}
		isModerator={$isModerator}
		canEdit={selectedUpdate.author_member_id === $session.memberId}
		topicId={$session.topicId}
		onClose={() => (selectedUpdate = null)}
		onUpdate={(updated) =>
			updates.update((all) => all.map((u) => (u.id === updated.id ? updated : u)))}
	/>
{/if}

<style>
	/* ── Full-bleed header ── */
	.topic-header {
		background: var(--color-text);
		padding: 2.25rem 0 1.75rem;
	}

	.topic-header--skeleton {
		background: var(--color-surface-hover);
	}

	.header-inner {
		max-width: var(--content-width);
		margin: 0 auto;
		padding: 0 1.5rem;
	}

	h1 {
		font-family: var(--font-display);
		font-size: var(--text-3xl);
		font-weight: 400;
		color: white;
		margin: 0 0 0.4rem;
		line-height: 1.1;
	}

	.header-meta {
		margin: 0;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.role-badge {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: rgba(255, 255, 255, 0.45);
		padding: 0.15rem 0.5rem;
		border: 1px solid rgba(255, 255, 255, 0.2);
		border-radius: 2px;
	}

	/* ── Content area ── */
	.content-wrapper {
		max-width: var(--content-width);
		margin: 0 auto;
		padding: 0 1.5rem 3rem;
	}

	/* ── Tab nav ── */
	nav {
		display: flex;
		gap: 0;
		margin: 0 0 1.5rem;
		border-bottom: 1px solid var(--color-border);
		padding-top: 0.25rem;
	}

	nav button {
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		padding: 0.65rem 1rem;
		cursor: pointer;
		border-radius: 0;
		letter-spacing: 0.05em;
		text-transform: uppercase;
		font-size: var(--text-xs);
		font-weight: 500;
		color: var(--color-text-muted);
		margin-bottom: -1px;
		transition:
			color 0.15s,
			border-color 0.15s;
	}

	nav button:hover {
		color: var(--color-text-secondary);
	}

	nav button.active {
		border-bottom-color: var(--color-accent);
		color: var(--color-accent);
	}

	/* ── Section labels ── */
	.section-label {
		font-size: var(--text-xs);
		font-weight: 600;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--color-text-muted);
		margin: 0 0 0.5rem;
	}

	hr {
		border: none;
		border-top: 1px solid var(--color-border);
		margin: 1.25rem 0;
	}

	/* ── List controls ── */
	.list-controls {
		display: flex;
		justify-content: space-between;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
	}

	.controls-left {
		display: flex;
		gap: 0.25rem;
		flex-wrap: wrap;
		align-items: center;
		flex: 1;
	}

	.controls-right {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		flex-shrink: 0;
	}

	.circle-filter-wrap {
		position: relative;
	}

	.circle-filter-btn {
		padding: 0.2rem 0.65rem;
		border-radius: 2px;
		font-size: var(--text-xs);
		border: 1px solid var(--color-border-strong);
		background: none;
		color: var(--color-text-secondary);
		cursor: pointer;
		transition: all 0.1s;
	}

	.circle-filter-btn.active {
		background: var(--color-accent-light);
		border-color: var(--color-accent);
		color: var(--color-accent);
	}

	.circle-popover {
		position: absolute;
		top: calc(100% + 0.35rem);
		left: 0;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 4px;
		padding: 0.5rem;
		z-index: 50;
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		min-width: 150px;
	}

	.popover-pill {
		padding: 0.2rem 0.65rem;
		border-radius: 2px;
		font-size: var(--text-xs);
		border: 1px solid var(--color-border-strong);
		background: none;
		color: var(--color-text-secondary);
		cursor: pointer;
		transition: all 0.1s;
		text-align: left;
	}

	.popover-pill.selected {
		background: var(--color-accent-light);
		border-color: var(--color-accent);
		color: var(--color-accent);
	}

	.clear-btn {
		font-size: var(--text-xs);
		color: var(--color-text-muted);
		background: none;
		border: none;
		cursor: pointer;
		padding: 0 0.25rem 0.25rem;
		text-align: left;
		border-bottom: 1px solid var(--color-border);
		margin-bottom: 0.1rem;
	}

	.clear-btn:hover {
		color: var(--color-accent);
	}

	.sort-select {
		padding: 0.2rem 0.4rem;
		border: 1px solid var(--color-border);
		border-radius: 2px;
		font-size: var(--text-xs);
		background: var(--color-surface);
		color: var(--color-text-secondary);
	}

	.deleted-toggle {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: var(--text-xs);
		color: var(--color-text-muted);
		cursor: pointer;
	}

	/* ── Skeleton nav ── */
	.skeleton-nav {
		display: flex;
		gap: 1.5rem;
		padding: 0.65rem 0 1rem;
		border-bottom: 1px solid var(--color-border);
		margin-bottom: 1.5rem;
	}

	/* ── Empty states ── */
	.empty-state {
		text-align: center;
		padding: 3.5rem 1rem;
	}

	.empty-headline {
		font-family: var(--font-display);
		font-size: var(--text-2xl);
		font-weight: 400;
		font-style: italic;
		color: var(--color-text-muted);
		margin: 0 0 0.5rem;
	}

	.empty-body {
		font-family: var(--font-body);
		font-size: var(--text-base);
		color: var(--color-text-muted);
		margin: 0;
		font-style: italic;
	}

	/* ── Danger button ── */
	.danger {
		background: var(--color-danger);
		color: white;
		border: none;
		padding: 0.5rem 1rem;
		border-radius: 2px;
		cursor: pointer;
		margin-top: 1rem;
		font-size: var(--text-sm);
		letter-spacing: 0.02em;
		transition: opacity 0.15s;
	}

	.danger:hover {
		opacity: 0.88;
	}
</style>
