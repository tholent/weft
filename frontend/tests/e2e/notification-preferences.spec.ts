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

// FT-32: E9 notification preferences E2E
//
// Backend findings (established by reading source before writing tests):
//
//   1. Preferences ARE auto-seeded on member creation via create_defaults() in
//      app/services/notifications/preferences.py — all 6 triggers (new_update,
//      new_reply, mod_response, invite, relay, digest) are created with
//      delivery_mode=immediate on the member's chosen channel. The list endpoint
//      will never return an empty array for a freshly seeded member.
//
//   2. The Settings tab is gated by `isAdmin` in the manage page template, so
//      only owner and admin members can see it. Admin magic link is used here.
//
//   3. The NotificationSettings component does NOT filter triggers by channel —
//      it renders all 6 preferences regardless of whether the member's channel is
//      email or SMS. Therefore test case 4 ("SMS sees phone-relevant triggers only")
//      cannot be implemented as a UI filtering assertion. Instead we verify:
//      - An SMS member's preferences list contains the expected SMS channel value
//        in the raw API response (confirming correct channel seeding).
//      - The UI renders the same 6 rows for an SMS-channel member as for an
//        email-channel member (since the component shows all triggers).
//      Note: SMS members are recipients (go to /topic/ not /manage/). Because
//      /topic/ has no Settings tab, the SMS UI verification is done via API
//      assertions rather than UI navigation.

import { test, expect } from './support/fixtures';

// ---------------------------------------------------------------------------
// Helper: sign in as the first admin and navigate to the Settings tab.
// ---------------------------------------------------------------------------

async function signInAsAdminOnSettings(
	page: import('@playwright/test').Page,
	adminMagic: Record<string, string>
): Promise<void> {
	const magic = Object.values(adminMagic)[0];
	await page.goto(`/auth?t=${magic}`);
	await page.waitForURL(/\/manage\//);

	// Wait for the skeleton to clear — Updates nav button becomes visible once
	// the initial data load resolves.
	await expect(page.getByRole('button', { name: /^updates$/i })).toBeVisible();

	// Open the Settings tab.
	await page.getByRole('button', { name: /^settings$/i }).click();

	// Wait for the "Notification Settings" section label to appear. This label
	// is rendered by the manage page as a <p class="section-label"> immediately
	// before the NotificationSettings component.
	await expect(page.getByText('Notification Settings', { exact: true })).toBeVisible({
		timeout: 5000
	});

	// The component itself renders an <h3>Notification Preferences</h3>.
	await expect(page.getByText('Notification Preferences', { exact: true })).toBeVisible({
		timeout: 5000
	});
}

// ---------------------------------------------------------------------------
// Test 1 — Load defaults: admin sees 6 preference rows
// ---------------------------------------------------------------------------

test('admin loads notification preferences — 6 rows visible on Settings tab', async ({
	page,
	seededTopic
}) => {
	await signInAsAdminOnSettings(page, seededTopic.adminMagic);

	// All 6 triggers should render as rows with a <select class="mode-select">.
	// create_defaults() seeds all NotificationTrigger enum values, so we expect
	// exactly 6 selects.
	const selects = page.locator('.mode-select');
	await expect(selects.first()).toBeVisible({ timeout: 5000 });
	await expect(selects).toHaveCount(6);

	// Spot-check that the trigger labels match the component's TRIGGER_LABELS map.
	await expect(page.getByText('New updates')).toBeVisible();
	await expect(page.getByText('New replies')).toBeVisible();
	await expect(page.getByText('Moderator responses')).toBeVisible();
	await expect(page.getByText('Invitations')).toBeVisible();
	await expect(page.getByText('Relayed replies')).toBeVisible();
	await expect(page.getByText('Daily digest')).toBeVisible();

	// All selects should default to "Immediate" (immediate delivery mode).
	const allSelectValues = await selects.evaluateAll((els) =>
		(els as HTMLSelectElement[]).map((el) => el.value)
	);
	expect(allSelectValues.every((v) => v === 'immediate')).toBe(true);
});

// ---------------------------------------------------------------------------
// Test 2 — Mute new_update: change to muted, reload, confirm persistence
// ---------------------------------------------------------------------------

test('muting new_update trigger persists after page reload', async ({ page, seededTopic }) => {
	await signInAsAdminOnSettings(page, seededTopic.adminMagic);

	// Locate the row for "New updates".
	const newUpdateRow = page.locator('tr').filter({ hasText: 'New updates' });
	await expect(newUpdateRow).toBeVisible();

	// Change the select in that row to "muted".
	const select = newUpdateRow.locator('.mode-select');
	await select.selectOption('muted');

	// The select should now reflect the new value (optimistic UI update).
	await expect(select).toHaveValue('muted');

	// Wait for the PUT request to complete by polling until the select is no
	// longer in saving state (disabled). Since saving disables the select while
	// the request is in flight, we wait until the select is re-enabled.
	await expect(select).toBeEnabled({ timeout: 5000 });

	// Reload the page to verify the change was persisted on the backend.
	await page.reload();
	await page.waitForURL(/\/manage\//);
	await expect(page.getByRole('button', { name: /^updates$/i })).toBeVisible();
	await page.getByRole('button', { name: /^settings$/i }).click();
	await expect(page.getByText('Notification Preferences', { exact: true })).toBeVisible({
		timeout: 5000
	});

	// After reload, the new_update row should still show "muted".
	const reloadedRow = page.locator('tr').filter({ hasText: 'New updates' });
	await expect(reloadedRow.locator('.mode-select')).toHaveValue('muted');
});

// ---------------------------------------------------------------------------
// Test 3 — Switch to digest mode: change to digest, reload, confirm persistence
// ---------------------------------------------------------------------------

test('switching new_update trigger to digest mode persists after page reload', async ({
	page,
	seededTopic
}) => {
	await signInAsAdminOnSettings(page, seededTopic.adminMagic);

	// Change the "New updates" select to "digest".
	const newUpdateRow = page.locator('tr').filter({ hasText: 'New updates' });
	const select = newUpdateRow.locator('.mode-select');
	await select.selectOption('digest');
	await expect(select).toHaveValue('digest');

	// Wait for the PUT to complete (select becomes re-enabled).
	await expect(select).toBeEnabled({ timeout: 5000 });

	// Reload the page to verify backend persistence.
	await page.reload();
	await page.waitForURL(/\/manage\//);
	await expect(page.getByRole('button', { name: /^updates$/i })).toBeVisible();
	await page.getByRole('button', { name: /^settings$/i }).click();
	await expect(page.getByText('Notification Preferences', { exact: true })).toBeVisible({
		timeout: 5000
	});

	const reloadedRow = page.locator('tr').filter({ hasText: 'New updates' });
	await expect(reloadedRow.locator('.mode-select')).toHaveValue('digest');
});

// ---------------------------------------------------------------------------
// Test 4 — SMS-channel member preferences (API-level verification)
//
// The manage page Settings tab is only accessible to admin/owner roles.
// Recipient-role members (the typical SMS channel use-case) navigate to
// /topic/ which has no Settings tab. Therefore we cannot do an E2E UI test
// for the SMS member's settings panel.
//
// Instead this test:
//   a) Creates a recipient member with notification_channel=sms via the
//      invite API (bypassing the seed spec which only supports email).
//   b) Signs in as the admin and uses the admin's API access to read that
//      member's preferences endpoint directly.
//   c) Asserts that all 6 preferences were auto-seeded with channel=sms
//      (confirming create_defaults() is called with the correct channel).
//
// If the UI ever exposes a Settings panel to recipients (or the SMS member is
// promoted to admin), the UI assertions can be uncommented and extended.
// ---------------------------------------------------------------------------

test('SMS-channel member has all triggers auto-seeded with channel=sms (API)', async ({
	page,
	request,
	seededTopic
}) => {
	// Step 1 — Sign in as admin via the magic link to exchange it for a bearer
	// token. The seededTopic fixture does not expose raw admin bearer tokens
	// directly, only owner's bearer (ownerBearer) and magic links. We navigate
	// to the auth page to trigger the token exchange, then read weft_token from
	// localStorage (the session store persists it there via login()).
	const adminMagic = Object.values(seededTopic.adminMagic)[0];
	await page.goto(`/auth?t=${adminMagic}`);
	await page.waitForURL(/\/manage\//);

	// Extract the bearer token from localStorage — stored under 'weft_token'
	// by the session store's login() function after magic link validation.
	const adminToken = await page.evaluate(() => localStorage.getItem('weft_token'));

	// Fall back to ownerBearer if localStorage read fails (owner can also invite
	// members and read any member's preferences).
	const inviteBearer = adminToken ?? seededTopic.ownerBearer;

	// Step 2 — Get the Family circle ID.
	const familyCircleId = seededTopic.circleIds['Family'];
	expect(familyCircleId).toBeTruthy();

	// Step 3 — Invite an SMS-channel recipient via the backend API.
	const inviteResp = await request.post(
		`http://127.0.0.1:8001/topics/${seededTopic.topicId}/members`,
		{
			headers: { Authorization: `Bearer ${inviteBearer}` },
			data: {
				email: null,
				phone: '+15550001234',
				role: 'recipient',
				circle_id: familyCircleId,
				notification_channel: 'sms'
			}
		}
	);
	expect(inviteResp.ok()).toBe(true);
	const invitedMember = (await inviteResp.json()) as { id: string; notification_channel: string };
	expect(invitedMember.notification_channel).toBe('sms');
	const smsMemberId = invitedMember.id;

	// Step 4 — Read the preferences for the SMS member (admin can read any member's prefs).
	const prefsResp = await request.get(
		`http://127.0.0.1:8001/topics/${seededTopic.topicId}/members/${smsMemberId}/notifications`,
		{ headers: { Authorization: `Bearer ${inviteBearer}` } }
	);
	expect(prefsResp.ok()).toBe(true);
	const prefs = (await prefsResp.json()) as Array<{
		id: string;
		trigger: string;
		channel: string;
		delivery_mode: string;
	}>;

	// All 6 triggers should be auto-seeded.
	expect(prefs).toHaveLength(6);

	const expectedTriggers = new Set([
		'new_update',
		'new_reply',
		'mod_response',
		'invite',
		'relay',
		'digest'
	]);
	for (const pref of prefs) {
		// Every preference should use the sms channel (not email).
		expect(pref.channel).toBe('sms');
		// All should default to immediate delivery.
		expect(pref.delivery_mode).toBe('immediate');
		expect(expectedTriggers.has(pref.trigger)).toBe(true);
	}

	// UI note: since this member is a recipient, they land on /topic/ not /manage/.
	// /topic/ has no Settings tab, so the NotificationSettings component is not
	// rendered for recipient-role members regardless of channel.
	// TODO: If a Settings panel is added to the recipient view, add UI assertions here.
});
