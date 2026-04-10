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
	import { session } from '$lib/stores/session';
	import { listNotificationPreferences, setNotificationPreference } from '$lib/api/notifications';
	import type { NotificationPreference, NotificationTrigger, DeliveryMode } from '$lib/types/notification';

	const TRIGGER_LABELS: Record<NotificationTrigger, string> = {
		new_update: 'New updates',
		new_reply: 'New replies',
		mod_response: 'Moderator responses',
		invite: 'Invitations',
		relay: 'Relayed replies',
		digest: 'Daily digest'
	};

	const DELIVERY_MODES: { value: DeliveryMode; label: string }[] = [
		{ value: 'immediate', label: 'Immediate' },
		{ value: 'digest', label: 'Digest' },
		{ value: 'muted', label: 'Muted' }
	];

	let preferences: NotificationPreference[] = [];
	let loading = true;
	let saving: string | null = null;
	let error: string | null = null;

	$: topicId = $session.topicId;
	$: memberId = $session.memberId;

	onMount(async () => {
		if (!topicId || !memberId) return;
		try {
			preferences = await listNotificationPreferences(topicId, memberId);
		} catch {
			error = 'Failed to load notification preferences.';
		} finally {
			loading = false;
		}
	});

	function getPref(trigger: NotificationTrigger): NotificationPreference | undefined {
		return preferences.find((p) => p.trigger === trigger);
	}

	async function handleChange(trigger: NotificationTrigger, mode: DeliveryMode) {
		if (!topicId || !memberId) return;
		const existing = getPref(trigger);
		if (!existing) return;

		saving = trigger;
		error = null;
		try {
			const updated = await setNotificationPreference(topicId, memberId, {
				channel: existing.channel,
				trigger,
				delivery_mode: mode
			});
			preferences = preferences.map((p) => (p.trigger === trigger ? updated : p));
		} catch {
			error = 'Failed to save preference. Please try again.';
		} finally {
			saving = null;
		}
	}
</script>

<div class="notification-settings">
	<h3>Notification Preferences</h3>

	{#if loading}
		<p class="status-text">Loading preferences...</p>
	{:else if error}
		<p class="error-text">{error}</p>
	{:else if preferences.length === 0}
		<p class="status-text">No notification preferences configured.</p>
	{:else}
		<table class="prefs-table">
			<thead>
				<tr>
					<th>Event</th>
					<th>Delivery</th>
				</tr>
			</thead>
			<tbody>
				{#each preferences as pref (pref.id)}
					<tr>
						<td class="trigger-label">{TRIGGER_LABELS[pref.trigger] ?? pref.trigger}</td>
						<td>
							<select
								value={pref.delivery_mode}
								disabled={saving === pref.trigger}
								on:change={(e) => handleChange(pref.trigger, (e.currentTarget as HTMLSelectElement).value as DeliveryMode)}
								class="mode-select"
								class:saving={saving === pref.trigger}
							>
								{#each DELIVERY_MODES as mode}
									<option value={mode.value}>{mode.label}</option>
								{/each}
							</select>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>

<style>
	.notification-settings {
		padding: 1rem 0;
	}

	h3 {
		font-size: 1rem;
		font-weight: 600;
		margin: 0 0 0.75rem;
	}

	.prefs-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.875rem;
	}

	.prefs-table th {
		text-align: left;
		padding: 0.25rem 0.5rem 0.5rem 0;
		font-weight: 600;
		color: var(--color-muted, #6b7280);
		border-bottom: 1px solid var(--color-border, #e5e7eb);
	}

	.prefs-table td {
		padding: 0.5rem 0.5rem 0.5rem 0;
		border-bottom: 1px solid var(--color-border, #e5e7eb);
		vertical-align: middle;
	}

	.trigger-label {
		color: var(--color-text, #111827);
	}

	.mode-select {
		padding: 0.25rem 0.5rem;
		border: 1px solid var(--color-border, #e5e7eb);
		border-radius: 0.25rem;
		background: var(--color-surface, #fff);
		font-size: 0.875rem;
		cursor: pointer;
	}

	.mode-select.saving {
		opacity: 0.6;
		cursor: wait;
	}

	.status-text {
		color: var(--color-muted, #6b7280);
		font-size: 0.875rem;
	}

	.error-text {
		color: var(--color-error, #dc2626);
		font-size: 0.875rem;
	}
</style>
