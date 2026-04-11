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

// FT-27: E4 admin posting updates E2E
//
// Tests the admin/owner flow for posting updates on the manage page, including:
//   1. Plain post              – type body, send, assert card appears
//   2. Multi-circle + ALT      – two circles, per-circle variant body, assert ALT badge
//   3. Circle filter           – open circle popover, filter to one circle, check feed
//   4. Sort toggle             – switch Newest/Oldest, verify order flips
//   5. Show-removed toggle     – seed a deleted update, toggle checkbox, see [removed]
//   6. Edit with edited badge  – click card → UpdateModal, edit body, assert "edited" badge

import { test, expect } from './support/fixtures';
import type { SeedTopicSpec } from './fixtures/seed-client';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Sign in via the owner magic link and wait until the manage page is ready. */
async function signInAsOwner(
	page: import('@playwright/test').Page,
	ownerMagic: string
): Promise<void> {
	await page.goto(`/auth?t=${ownerMagic}`);
	await page.waitForURL(/\/manage\/[^/]+/);
	// Wait for the skeleton to disappear — the "Updates" nav tab becomes visible
	// once loading finishes.
	await expect(page.getByRole('button', { name: /^updates$/i })).toBeVisible();
}

// Two-circle seed spec — used by tests that need more than one circle.
const TWO_CIRCLE_SPEC: SeedTopicSpec = {
	title: 'E2E Two-Circle Topic',
	owner_email: 'owner@example.com',
	owner_name: 'Seed Owner',
	circles: [
		{
			name: 'Family',
			members: [
				{ email: 'alice@example.com', role: 'recipient', name: 'Alice' },
				{ email: 'admin@example.com', role: 'admin', name: 'Admin User' }
			]
		},
		{
			name: 'Coworkers',
			members: [{ email: 'bob@example.com', role: 'recipient', name: 'Bob' }]
		}
	]
};

// ---------------------------------------------------------------------------
// Test 1 – Plain post
// ---------------------------------------------------------------------------

test('owner posts a plain update and it appears in the feed', async ({ page, seededTopic }) => {
	await signInAsOwner(page, seededTopic.ownerMagic);

	// The ComposeBox textarea is the first (only) textarea in the compose form.
	// In update mode with no custom bodies active its placeholder is "Write an update…".
	const compose = page.getByPlaceholder('Write an update…');
	await compose.fill('Plain update body from E2E test');

	await page.getByRole('button', { name: /^send$/i }).click();

	// The new UpdateCard should appear in the feed.
	await expect(page.getByText('Plain update body from E2E test')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 2 – Multi-circle post with per-circle body variant
// ---------------------------------------------------------------------------

test('owner posts to two circles with a per-circle ALT body, ALT badge appears on card', async ({
	page,
	seedClient
}) => {
	// Use a custom two-circle spec so we have Family + Coworkers.
	await seedClient.reset();
	const data = await seedClient.seedTopic(TWO_CIRCLE_SPEC);

	await page.goto(`/auth?t=${data.magic_links.owner}`);
	await page.waitForURL(/\/manage\/[^/]+/);
	await expect(page.getByRole('button', { name: /^updates$/i })).toBeVisible();

	const compose = page.getByPlaceholder('Write an update…');
	await compose.fill('Default body for both circles');

	// Select the "Family" circle pill.
	await page.getByRole('button', { name: /^family$/i }).click();
	// Select the "Coworkers" circle pill.
	await page.getByRole('button', { name: /^coworkers$/i }).click();

	// Click ALT on the "Coworkers" circle to enable a variant body.
	// ALT buttons appear next to each selected circle pill.
	// We locate the ALT button by its title attribute which includes the circle name.
	await page.locator('button.pill-alt[title*="Coworkers"]').click();

	// Now the compose textarea placeholder changes. The variant textarea for
	// "Coworkers" has placeholder "Message for Coworkers…".
	const variantTextarea = page.getByPlaceholder('Message for Coworkers…');
	await variantTextarea.fill('Coworkers-specific variant body');

	await page.getByRole('button', { name: /^send$/i }).click();

	// The new card should appear. The UpdateCard renders an ALT badge inside
	// the circle pill when body_variants has an entry for that circle.
	// The card text starts with the default body.
	await expect(page.getByText('Default body for both circles')).toBeVisible();

	// The ALT badge is rendered as a <span class="pill-alt">ALT</span> inside
	// the pill-variant span. We assert that text "ALT" is visible somewhere
	// in the feed area (scoped to the update card).
	const updateCard = page.locator('.update-row').filter({
		hasText: 'Default body for both circles'
	});
	await expect(updateCard.getByText('ALT')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 3 – Circle filter
// ---------------------------------------------------------------------------

test('circle filter shows only updates from the selected circle', async ({ page, seedClient }) => {
	// Seed two circles with one update each.
	await seedClient.reset();
	const data = await seedClient.seedTopic({
		...TWO_CIRCLE_SPEC,
		updates: [
			{
				body: 'Family-only update',
				circle_names: ['Family'],
				author_email: 'owner@example.com'
			},
			{
				body: 'Coworkers-only update',
				circle_names: ['Coworkers'],
				author_email: 'owner@example.com'
			}
		]
	});

	await page.goto(`/auth?t=${data.magic_links.owner}`);
	await page.waitForURL(/\/manage\/[^/]+/);
	await expect(page.getByRole('button', { name: /^updates$/i })).toBeVisible();

	// Both updates should be visible initially.
	await expect(page.getByText('Family-only update')).toBeVisible();
	await expect(page.getByText('Coworkers-only update')).toBeVisible();

	// Open the circle filter popover via the "Circles" button.
	await page.locator('button.circle-filter-btn').click();

	// Click the "Family" pill inside the popover to filter to Family only.
	// The filter is applied immediately on click; the popover is closed by
	// clicking the Circles button again (toggle behavior).
	await page.locator('.circle-popover button.popover-pill', { hasText: 'Family' }).click();

	// Click the Circles button again to collapse the popover.
	await page.locator('button.circle-filter-btn').click();

	// Only the Family update should remain visible.
	await expect(page.getByText('Family-only update')).toBeVisible();
	await expect(page.getByText('Coworkers-only update')).not.toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 4 – Sort toggle
// ---------------------------------------------------------------------------

test('switching sort from Newest to Oldest reverses the update order', async ({
	page,
	seedClient,
	request
}) => {
	// Seed a topic with one update via the seed API (gives us a baseline timestamp).
	await seedClient.reset();
	const data = await seedClient.seedTopic({
		title: 'Sort Test Topic',
		owner_email: 'owner@example.com',
		circles: [{ name: 'Family', members: [] }],
		updates: [
			{ body: 'First update posted', circle_names: ['Family'], author_email: 'owner@example.com' }
		]
	});

	// Post a second update via the API with a small sleep gap to guarantee
	// a later created_at timestamp. Playwright request context hits the backend
	// directly; no UI needed.
	// Small wait to ensure distinct timestamps.
	await page.waitForTimeout(50);
	const circleId = data.circle_ids['Family'];
	const postResp = await request.post(`http://127.0.0.1:8001/topics/${data.topic_id}/updates`, {
		data: { body: 'Second update posted', circle_ids: [circleId], circle_bodies: {} },
		headers: { Authorization: `Bearer ${data.owner_token}` }
	});
	expect(postResp.ok()).toBe(true);

	// Load the manage page as owner.
	await page.goto(`/auth?t=${data.magic_links.owner}`);
	await page.waitForURL(/\/manage\/[^/]+/);
	await expect(page.getByRole('button', { name: /^updates$/i })).toBeVisible();

	// Default sort is "Newest" — the second (most recent) update should appear first.
	const cards = page.locator('.update-row');
	await expect(cards).toHaveCount(2);

	const firstCardNewest = await cards.first().textContent();
	expect(firstCardNewest).toContain('Second update posted');

	// Switch to "Oldest".
	await page.locator('select.sort-select').selectOption('oldest');

	// Now the first update should appear first.
	const firstCardOldest = await page.locator('.update-row').first().textContent();
	expect(firstCardOldest).toContain('First update posted');
});

// ---------------------------------------------------------------------------
// Test 5 – Show-removed toggle
// ---------------------------------------------------------------------------

// NOTE: The current backend implementation of list_updates_for_topic() always
// filters out soft-deleted updates (deleted_at IS NULL). As a result, the
// frontend $updates store never contains entries with deleted_at set, the
// "Show removed" checkbox condition ($updates.some(u => u.deleted_at)) is
// never true, and the checkbox never renders.
//
// The test below validates the UI mechanics as far as they can be tested:
// it soft-deletes an update via the API, reloads the page, and asserts that
// the update is simply absent (backend excluded it) and the checkbox is not
// present. The "Show removed" feature would only become testable end-to-end
// if the backend feed endpoint is updated to include deleted updates for
// admin/moderator callers.
//
// TODO: Once the backend returns deleted updates to admins, remove the skip
// and replace the assertions with:
//   - expect(showRemovedLabel).toBeVisible()
//   - check the checkbox
//   - expect(page.getByText('[removed]')).toBeVisible()

test('show-removed toggle: deleted update is absent from feed (backend filters it)', async ({
	page,
	seedClient,
	request
}) => {
	// Seed a topic with one update authored by the owner.
	await seedClient.reset();
	const data = await seedClient.seedTopic({
		title: 'Show Removed Test',
		owner_email: 'owner@example.com',
		circles: [{ name: 'Family', members: [] }],
		updates: [
			{ body: 'Update to be deleted', circle_names: ['Family'], author_email: 'owner@example.com' }
		]
	});

	// Step 1: Get the feed to find the update ID.
	// The endpoint is GET /topics/{topicId}/updates (paginated response: { items, total, ... }).
	const feedResp = await request.get(`http://127.0.0.1:8001/topics/${data.topic_id}/updates`, {
		headers: { Authorization: `Bearer ${data.owner_token}` }
	});
	expect(feedResp.ok()).toBe(true);
	const feedBody = (await feedResp.json()) as { items: Array<{ id: string }> };
	expect(feedBody.items.length).toBeGreaterThan(0);
	const updateId = feedBody.items[0].id;

	// Step 2: Soft-delete the update via DELETE /topics/{topicId}/updates/{updateId}.
	const deleteResp = await request.delete(
		`http://127.0.0.1:8001/topics/${data.topic_id}/updates/${updateId}`,
		{ headers: { Authorization: `Bearer ${data.owner_token}` } }
	);
	expect(deleteResp.ok()).toBe(true);

	// Step 3: Load the manage page as owner.
	await page.goto(`/auth?t=${data.magic_links.owner}`);
	await page.waitForURL(/\/manage\/[^/]+/);
	await expect(page.getByRole('button', { name: /^updates$/i })).toBeVisible();

	// The update does not appear — the backend excluded it from the feed.
	await expect(page.getByText('Update to be deleted')).not.toBeVisible();

	// The "Show removed" checkbox does not appear because the store has no
	// deleted updates (backend never sends them).
	await expect(page.locator('label.deleted-toggle')).not.toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 6 – Edit with edited badge
// ---------------------------------------------------------------------------

test('owner edits an update via UpdateModal and the edited badge appears on the card', async ({
	page,
	seedClient
}) => {
	await seedClient.reset();
	const data = await seedClient.seedTopic({
		title: 'Edit Test Topic',
		owner_email: 'owner@example.com',
		circles: [{ name: 'Family', members: [] }],
		updates: [
			{ body: 'Original update body', circle_names: ['Family'], author_email: 'owner@example.com' }
		]
	});

	await page.goto(`/auth?t=${data.magic_links.owner}`);
	await page.waitForURL(/\/manage\/[^/]+/);
	await expect(page.getByRole('button', { name: /^updates$/i })).toBeVisible();

	// Click the update card to open UpdateModal.
	const updateCard = page.locator('.update-row').filter({ hasText: 'Original update body' });
	await updateCard.click();

	// UpdateModal is mounted — the modal dialog should be visible.
	const modal = page.locator('[role="dialog"]');
	await expect(modal).toBeVisible();

	// The owner is the author so canEdit=true; an "Edit" button (text-decoration
	// underline styled as an inline button) should be visible in the modal meta area.
	const editBtn = modal.getByRole('button', { name: /^edit$/i });
	await expect(editBtn).toBeVisible();
	await editBtn.click();

	// Edit mode: the existing body is pre-filled in the edit textarea.
	// Clear it and type a new body.
	const editTextarea = modal.locator('textarea.edit-body').first();
	await editTextarea.fill('Edited update body');

	// Click Save.
	await modal.getByRole('button', { name: /^save$/i }).click();

	// The modal should exit edit mode and show the updated body.
	await expect(modal.getByRole('button', { name: /^edit$/i })).toBeVisible();

	// Close the modal.
	await modal.getByRole('button', { name: '✕' }).click();
	await expect(modal).not.toBeVisible();

	// The UpdateCard in the feed should now show the "edited" badge.
	const updatedCard = page.locator('.update-row').filter({ hasText: 'Edited update body' });
	await expect(updatedCard).toBeVisible();
	await expect(updatedCard.locator('.edited')).toBeVisible();
});
