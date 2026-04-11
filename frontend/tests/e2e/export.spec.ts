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

// FT-34: E11 export E2E
//
// Tests the topic export flow available on the manage page Settings tab:
//   1. Owner triggers download — filename is weft-export-{topicId}.json.
//   2. Admin sees the Export Topic Data button on the Settings tab.
//   3. Moderator does NOT see the Export Topic Data button (no Settings tab).
//
// Role-gating note: The ExportButton is rendered inside the Settings tab under
// `{#if $isAdmin && $session.topicId}`. The Settings tab itself is only shown
// when `$isAdmin` is true (owners and admins). Moderators have the 'moderator'
// role which does not satisfy $isAdmin, so they never see the Settings tab or
// the export button.

import { test, expect } from './support/fixtures';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Navigate to the Settings tab as the given user via magic link. */
async function goToSettingsTab(
	page: import('@playwright/test').Page,
	magic: string
): Promise<void> {
	await page.goto(`/auth?t=${magic}`);
	await page.waitForURL(/\/manage\//);
	// Wait for the skeleton to resolve — the Updates nav button appears first.
	await expect(
		page.getByRole('navigation').getByRole('button', { name: /^updates$/i })
	).toBeVisible();
	// Click the Settings tab (only visible to admin/owner).
	await page
		.getByRole('navigation')
		.getByRole('button', { name: /^settings$/i })
		.click();
	// Confirm the Settings heading renders.
	await expect(page.getByRole('heading', { name: /^settings$/i })).toBeVisible();
}

// ---------------------------------------------------------------------------
// Case 1: Owner triggers download — filename matches topic ID.
//
// The ExportButton calls downloadTopicExport(), which fetches /export, builds
// a Blob, attaches it to an anchor with the `download` attribute, and clicks
// it. Playwright captures this via page.waitForEvent('download').
// ---------------------------------------------------------------------------

test('owner downloads topic export with correct filename', async ({ page, seededTopic }) => {
	await goToSettingsTab(page, seededTopic.ownerMagic);

	// The Export section label should be visible. Scope the text query to the
	// .section-label class so it does not collide with the "Export Topic Data"
	// button, which also matches /export/.
	await expect(page.locator('.section-label', { hasText: /^Export$/ })).toBeVisible();

	const exportBtn = page.getByRole('button', { name: /export topic data/i });
	await expect(exportBtn).toBeVisible();

	const [download] = await Promise.all([page.waitForEvent('download'), exportBtn.click()]);

	expect(download.suggestedFilename()).toBe(`weft-export-${seededTopic.topicId}.json`);
});

// ---------------------------------------------------------------------------
// Case 2: Admin sees the Export Topic Data button.
//
// Admins satisfy $isAdmin so the Settings tab is shown and the ExportButton
// is rendered inside it.
// ---------------------------------------------------------------------------

test('admin sees the export button on the settings tab', async ({ page, seededTopic }) => {
	const adminMagic = seededTopic.adminMagic['admin@example.com'];
	await goToSettingsTab(page, adminMagic);

	const exportBtn = page.getByRole('button', { name: /export topic data/i });
	await expect(exportBtn).toBeVisible();
});

// ---------------------------------------------------------------------------
// Case 3: Moderator does NOT see the Export Topic Data button.
//
// Moderators do not satisfy $isAdmin, so the Settings tab is never rendered
// in the navigation. There is no path for a moderator to reach the export
// button, and the button should not appear anywhere on the page.
// ---------------------------------------------------------------------------

test('moderator does not see the export button', async ({ page, seededTopic }) => {
	const modMagic = seededTopic.moderatorMagic['mod@example.com'];
	await page.goto(`/auth?t=${modMagic}`);
	await page.waitForURL(/\/manage\//);
	// Wait for the page to finish loading (Updates tab renders content).
	await expect(
		page.getByRole('navigation').getByRole('button', { name: /^updates$/i })
	).toBeVisible();

	// The Settings tab button should not be in the DOM for moderators.
	await expect(
		page.getByRole('navigation').getByRole('button', { name: /^settings$/i })
	).not.toBeVisible();

	// The export button itself should not appear anywhere on the page.
	expect(await page.getByRole('button', { name: /export topic data/i }).count()).toBe(0);
});
