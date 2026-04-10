// Copyright 2026 Chris Wells <chris@tholent.com>
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/svelte';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/msw-server';
import { login, session } from '$lib/stores/session';
import NotificationSettings from '$lib/components/NotificationSettings.svelte';
import { makeNotificationPreference } from '../fixtures';
import type { MemberRole } from '$lib/types/member';

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

const TEST_TOPIC_ID = 'topic-ns-1';
const TEST_MEMBER_ID = 'member-ns-1';
const PREFS_URL = `http://localhost/api/topics/${TEST_TOPIC_ID}/members/${TEST_MEMBER_ID}/notifications`;

/** Prime the session store with known topic/member IDs before each test. */
function primeSession() {
	login('test-token', TEST_MEMBER_ID, 'recipient' as MemberRole, TEST_TOPIC_ID);
}

beforeEach(() => {
	primeSession();
});

// ---------------------------------------------------------------------------
// onMount: preferences load
// ---------------------------------------------------------------------------

describe('NotificationSettings — onMount preferences load', () => {
	it('fetches GET /notifications on mount and renders trigger labels', async () => {
		const pref1 = makeNotificationPreference({
			id: 'pref-1',
			trigger: 'new_update',
			channel: 'email',
			delivery_mode: 'immediate'
		});
		const pref2 = makeNotificationPreference({
			id: 'pref-2',
			trigger: 'new_reply',
			channel: 'email',
			delivery_mode: 'muted'
		});

		server.use(
			http.get(PREFS_URL, () => {
				return HttpResponse.json([pref1, pref2]);
			})
		);

		render(NotificationSettings);

		// Initially shows loading state
		expect(screen.getByText('Loading preferences...')).toBeInTheDocument();

		// After fetch resolves, the table rows appear with trigger labels
		await waitFor(() => {
			expect(screen.getByText('New updates')).toBeInTheDocument();
		});

		expect(screen.getByText('New replies')).toBeInTheDocument();
	});

	it('renders a select element for each loaded preference', async () => {
		const prefs = [
			makeNotificationPreference({ id: 'p-1', trigger: 'new_update', delivery_mode: 'immediate' }),
			makeNotificationPreference({ id: 'p-2', trigger: 'new_reply', delivery_mode: 'digest' }),
			makeNotificationPreference({ id: 'p-3', trigger: 'mod_response', delivery_mode: 'muted' })
		];

		server.use(
			http.get(PREFS_URL, () => {
				return HttpResponse.json(prefs);
			})
		);

		render(NotificationSettings);

		await waitFor(() => {
			const selects = document.querySelectorAll('select.mode-select');
			expect(selects).toHaveLength(3);
		});
	});

	it('shows empty-state message when the preferences list is empty', async () => {
		server.use(
			http.get(PREFS_URL, () => {
				return HttpResponse.json([]);
			})
		);

		render(NotificationSettings);

		await waitFor(() => {
			expect(
				screen.getByText('No notification preferences configured.')
			).toBeInTheDocument();
		});
	});

	it('shows error message when the GET request fails', async () => {
		server.use(
			http.get(PREFS_URL, () => {
				return HttpResponse.json({ detail: 'Server error' }, { status: 500 });
			})
		);

		render(NotificationSettings);

		await waitFor(() => {
			expect(
				screen.getByText('Failed to load notification preferences.')
			).toBeInTheDocument();
		});
	});

	it('does nothing when session has no topicId or memberId', async () => {
		// Override session to have null IDs — no fetch should be made.
		// Use session.set directly to bypass login()'s string-only signature.
		session.set({ token: 'test-token', memberId: null, role: 'recipient' as MemberRole, topicId: null });

		// If a GET were fired and unhandled, MSW would throw (onUnhandledRequest: 'error').
		// The component's onMount guard returns early without setting loading=false,
		// so it stays in the loading state.
		render(NotificationSettings);

		// Give time for any erroneous fetch to fire
		await new Promise((r) => setTimeout(r, 50));

		// The loading text disappears only after preferences load; since no fetch ran
		// the component keeps showing "Loading preferences..."
		expect(screen.getByText('Loading preferences...')).toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// Delivery mode select — value reflects loaded preference
// ---------------------------------------------------------------------------

describe('NotificationSettings — select reflects loaded delivery_mode', () => {
	it('select value matches the delivery_mode returned by the API', async () => {
		const pref = makeNotificationPreference({
			id: 'pref-dm-1',
			trigger: 'new_update',
			delivery_mode: 'digest'
		});

		server.use(
			http.get(PREFS_URL, () => {
				return HttpResponse.json([pref]);
			})
		);

		render(NotificationSettings);

		await waitFor(() => {
			expect(screen.getByText('New updates')).toBeInTheDocument();
		});

		const select = document.querySelector('select.mode-select') as HTMLSelectElement;
		expect(select).not.toBeNull();
		expect(select.value).toBe('digest');
	});
});

// ---------------------------------------------------------------------------
// Trigger toggle: changing delivery mode fires PUT with full payload
// ---------------------------------------------------------------------------

describe('NotificationSettings — delivery mode change fires PUT', () => {
	it('sends PUT with full payload when the select value changes', async () => {
		const originalPref = makeNotificationPreference({
			id: 'pref-put-1',
			trigger: 'new_update',
			channel: 'email',
			delivery_mode: 'immediate'
		});
		const updatedPref = makeNotificationPreference({
			id: 'pref-put-1',
			trigger: 'new_update',
			channel: 'email',
			delivery_mode: 'muted'
		});

		let capturedBody: unknown = null;

		server.use(
			http.get(PREFS_URL, () => {
				return HttpResponse.json([originalPref]);
			}),
			http.put(PREFS_URL, async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(updatedPref);
			})
		);

		render(NotificationSettings);

		// Wait for preferences to load
		await waitFor(() => {
			expect(screen.getByText('New updates')).toBeInTheDocument();
		});

		const select = document.querySelector('select.mode-select') as HTMLSelectElement;
		expect(select).not.toBeNull();
		expect(select.value).toBe('immediate');

		// Simulate changing the select to 'muted'
		await fireEvent.change(select, { target: { value: 'muted' } });

		// Wait for the PUT to be captured
		await waitFor(() => {
			expect(capturedBody).not.toBeNull();
		});

		// The PUT body must include ALL three required fields
		expect(capturedBody).toEqual({
			channel: 'email',
			trigger: 'new_update',
			delivery_mode: 'muted'
		});
	});

	it('PUT payload carries channel from the existing preference, not a default', async () => {
		const smsPref = makeNotificationPreference({
			id: 'pref-sms-1',
			trigger: 'new_reply',
			channel: 'sms',
			delivery_mode: 'immediate'
		});
		const updatedPref = makeNotificationPreference({
			...smsPref,
			delivery_mode: 'digest'
		});

		let capturedBody: unknown = null;

		server.use(
			http.get(PREFS_URL, () => {
				return HttpResponse.json([smsPref]);
			}),
			http.put(PREFS_URL, async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(updatedPref);
			})
		);

		render(NotificationSettings);

		await waitFor(() => {
			expect(screen.getByText('New replies')).toBeInTheDocument();
		});

		const select = document.querySelector('select.mode-select') as HTMLSelectElement;
		await fireEvent.change(select, { target: { value: 'digest' } });

		await waitFor(() => {
			expect(capturedBody).not.toBeNull();
		});

		// channel must be 'sms' — taken from the existing pref, not defaulted to 'email'
		expect(capturedBody).toHaveProperty('channel', 'sms');
		expect(capturedBody).toHaveProperty('trigger', 'new_reply');
		expect(capturedBody).toHaveProperty('delivery_mode', 'digest');
	});

	it('updates the select value in the DOM after a successful PUT', async () => {
		const originalPref = makeNotificationPreference({
			id: 'pref-dom-1',
			trigger: 'new_update',
			channel: 'email',
			delivery_mode: 'immediate'
		});
		const updatedPref = makeNotificationPreference({
			...originalPref,
			delivery_mode: 'muted'
		});

		server.use(
			http.get(PREFS_URL, () => {
				return HttpResponse.json([originalPref]);
			}),
			http.put(PREFS_URL, async () => {
				return HttpResponse.json(updatedPref);
			})
		);

		render(NotificationSettings);

		await waitFor(() => {
			expect(screen.getByText('New updates')).toBeInTheDocument();
		});

		const select = document.querySelector('select.mode-select') as HTMLSelectElement;
		await fireEvent.change(select, { target: { value: 'muted' } });

		// After PUT resolves, the store is updated and the select should reflect 'muted'
		await waitFor(() => {
			const updatedSelect = document.querySelector('select.mode-select') as HTMLSelectElement;
			expect(updatedSelect.value).toBe('muted');
		});
	});

	it('shows error text when the PUT request fails', async () => {
		const pref = makeNotificationPreference({
			id: 'pref-err-1',
			trigger: 'new_update',
			channel: 'email',
			delivery_mode: 'immediate'
		});

		server.use(
			http.get(PREFS_URL, () => {
				return HttpResponse.json([pref]);
			}),
			http.put(PREFS_URL, () => {
				return HttpResponse.json({ detail: 'Server error' }, { status: 500 });
			})
		);

		render(NotificationSettings);

		await waitFor(() => {
			expect(screen.getByText('New updates')).toBeInTheDocument();
		});

		const select = document.querySelector('select.mode-select') as HTMLSelectElement;
		await fireEvent.change(select, { target: { value: 'digest' } });

		await waitFor(() => {
			expect(
				screen.getByText('Failed to save preference. Please try again.')
			).toBeInTheDocument();
		});
	});
});

// ---------------------------------------------------------------------------
// Full payload invariant — all three fields present regardless of which changed
// ---------------------------------------------------------------------------

describe('NotificationSettings — full payload PUT invariant', () => {
	it('includes channel, trigger, and delivery_mode in every PUT', async () => {
		const prefs = [
			makeNotificationPreference({
				id: 'full-1',
				trigger: 'invite',
				channel: 'email',
				delivery_mode: 'immediate'
			}),
			makeNotificationPreference({
				id: 'full-2',
				trigger: 'digest',
				channel: 'sms',
				delivery_mode: 'digest'
			})
		];

		const capturedBodies: unknown[] = [];

		server.use(
			http.get(PREFS_URL, () => {
				return HttpResponse.json(prefs);
			}),
			http.put(PREFS_URL, async ({ request }) => {
				const body = await request.json();
				capturedBodies.push(body);
				// Return updated version matching the trigger
				const b = body as { trigger: string; channel: string; delivery_mode: string };
				const updated = prefs.find((p) => p.trigger === b.trigger)!;
				return HttpResponse.json({ ...updated, delivery_mode: b.delivery_mode });
			})
		);

		render(NotificationSettings);

		await waitFor(() => {
			expect(screen.getByText('Invitations')).toBeInTheDocument();
		});

		// Change the first select (invite pref)
		const selects = document.querySelectorAll('select.mode-select');
		expect(selects).toHaveLength(2);

		await fireEvent.change(selects[0], { target: { value: 'muted' } });

		await waitFor(() => {
			expect(capturedBodies).toHaveLength(1);
		});

		const body = capturedBodies[0] as Record<string, unknown>;
		expect(body).toHaveProperty('channel');
		expect(body).toHaveProperty('trigger');
		expect(body).toHaveProperty('delivery_mode');
		// Confirm exact values
		expect(body.channel).toBe('email');
		expect(body.trigger).toBe('invite');
		expect(body.delivery_mode).toBe('muted');
	});
});
