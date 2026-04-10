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

// FT-30: E7 circles management E2E
//
// Tests the owner/admin flow for managing circles on the manage page:
//   1. Create     – fill name, click "Add Circle", assert circle appears
//   2. Rename     – click Edit, change name, click Save, assert new name visible
//   3. Scoped title – enter edit mode, set scoped title, save, assert ".scoped" span visible
//   4. Delete     – handle window.confirm via Playwright dialog listener, assert circle removed
//   5. Compose picker after delete – switch to Updates tab, verify deleted circle absent
//
// NOTE on "soft-delete": The PLAN.md references "soft-deleted circles absent from compose
// picker". CircleManager performs HARD delete (no deleted_at concept). deleteCircle() calls
// the REST DELETE endpoint and then refreshes $circles from the API. A deleted circle simply
// disappears from $circles, which is the source of truth for ComposeBox.targetCircles. There
// is no soft-delete filter to test — the circle is just gone. The compose-picker assertion
// below is therefore straightforwardly: after deletion the circle pill must not appear.

import { test, expect } from './support/fixtures';

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

/** Navigate to the manage page via owner magic link and wait for the UI to load. */
async function signInAsOwner(
  page: import('@playwright/test').Page,
  ownerMagic: string
): Promise<void> {
  await page.goto(`/auth?t=${ownerMagic}`);
  await page.waitForURL(/\/manage\/[^/]+/);
  // Wait until the Updates tab button is visible — signals loading is complete.
  await expect(page.getByRole('button', { name: /^updates$/i })).toBeVisible();
}

/** Switch to the Circles tab (only visible to admins+). */
async function openCirclesTab(page: import('@playwright/test').Page): Promise<void> {
  // Scope to the nav so we don't collide with the in-page "Circles" filter
  // button that appears on the Updates tab.
  await page.getByRole('navigation').getByRole('button', { name: /^circles$/i }).click();
  // The CircleManager section heading becomes the orientation anchor.
  await expect(page.locator('section h2', { hasText: 'Circles' })).toBeVisible();
}

// ---------------------------------------------------------------------------
// Test 1 – Create a circle
// ---------------------------------------------------------------------------

test('owner creates a new circle and it appears in the list', async ({ page, seededTopic }) => {
  await signInAsOwner(page, seededTopic.ownerMagic);
  await openCirclesTab(page);

  // Fill the "New circle name" input and submit.
  await page.getByPlaceholder('New circle name').fill('Coworkers');
  // Submit the create form via Enter on the name input. The "Add Circle"
  // button is sometimes pointer-intercepted by the scoped-title input on
  // narrower viewports, so we let the form's on:submit handler do the work.
  await page.getByPlaceholder('New circle name').press('Enter');

  // The new circle should appear as a <strong> element in a circle-row.
  await expect(page.locator('.circle-row strong', { hasText: 'Coworkers' })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 2 – Rename a circle
// ---------------------------------------------------------------------------

test('owner renames an existing circle and the new name is displayed', async ({
  page,
  seededTopic
}) => {
  await signInAsOwner(page, seededTopic.ownerMagic);
  await openCirclesTab(page);

  // The seed creates a "Family" circle. Find its row and click Edit.
  // Once edit mode begins, the <strong>Family</strong> is replaced with an
  // input, so the row identifier changes — re-locate the editing row by its
  // Save button afterwards.
  const familyRow = page
    .locator('.circle-row')
    .filter({ has: page.locator('strong', { hasText: 'Family' }) });
  await familyRow.getByRole('button', { name: /^edit$/i }).click();

  const editingRow = page
    .locator('.circle-row')
    .filter({ has: page.getByRole('button', { name: /^save$/i }) });

  const nameInput = editingRow.getByPlaceholder('Name');
  await nameInput.fill('Extended Family');

  // Use force:true because the Scoped title input pointer-intercepts the
  // Save button on narrow viewports.
  await editingRow.getByRole('button', { name: /^save$/i }).click({ force: true });

  // After save, the row should display the updated name.
  await expect(page.locator('.circle-row strong', { hasText: 'Extended Family' })).toBeVisible();
  // The old exact name should no longer appear (use anchored regex —
  // 'Extended Family' contains 'Family' as a substring).
  await expect(page.locator('.circle-row strong', { hasText: /^Family$/ })).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// Test 3 – Set a scoped title
// ---------------------------------------------------------------------------

test('owner sets a scoped title on a circle and the .scoped span is shown', async ({
  page,
  seededTopic
}) => {
  await signInAsOwner(page, seededTopic.ownerMagic);
  await openCirclesTab(page);

  // Enter edit mode for the "Family" circle. The row identity changes once
  // the <strong> is swapped for inputs, so re-locate via the Save button.
  const familyRow = page
    .locator('.circle-row')
    .filter({ has: page.locator('strong', { hasText: 'Family' }) });
  await familyRow.getByRole('button', { name: /^edit$/i }).click();

  const editingRow = page
    .locator('.circle-row')
    .filter({ has: page.getByRole('button', { name: /^save$/i }) });

  const scopedInput = editingRow.getByPlaceholder('Scoped title (optional)');
  await scopedInput.fill('Family Tier');

  // Use force:true because the Scoped title input pointer-intercepts the
  // Save button on narrow viewports.
  await editingRow.getByRole('button', { name: /^save$/i }).click({ force: true });

  // CircleManager renders: {#if circle.scoped_title}<span class="scoped">({circle.scoped_title})</span>
  // So the rendered text is "(Family Tier)".
  await expect(page.locator('.circle-row .scoped', { hasText: '(Family Tier)' })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 4 – Delete a circle with window.confirm accepted
// ---------------------------------------------------------------------------

test('owner deletes a circle and it is removed from the list', async ({ page, seededTopic }) => {
  await signInAsOwner(page, seededTopic.ownerMagic);
  await openCirclesTab(page);

  // First create a circle so we have a safe target to delete without
  // disrupting seed data used by other assertions.
  await page.getByPlaceholder('New circle name').fill('ToDelete');
  // Submit the create form via Enter on the name input. The "Add Circle"
  // button is sometimes pointer-intercepted by the scoped-title input on
  // narrower viewports, so we let the form's on:submit handler do the work.
  await page.getByPlaceholder('New circle name').press('Enter');
  await expect(page.locator('.circle-row strong', { hasText: 'ToDelete' })).toBeVisible();

  // Set up the dialog listener BEFORE clicking Delete.
  // CircleManager calls window.confirm('Delete this circle?') — Playwright
  // intercepts it via the 'dialog' event. We must register the handler first.
  page.once('dialog', (dialog) => dialog.accept());

  // Click the Delete button on the ToDelete row.
  const toDeleteRow = page.locator('.circle-row').filter({
    has: page.locator('strong', { hasText: 'ToDelete' })
  });
  await toDeleteRow.getByRole('button', { name: /^delete$/i }).click();

  // After the confirmed delete, the circle should be absent from the list.
  await expect(page.locator('.circle-row strong', { hasText: 'ToDelete' })).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// Test 5 – Deleted circle absent from compose picker
// ---------------------------------------------------------------------------
//
// NOTE: This tests HARD delete, not soft-delete. CircleManager has no deleted_at
// concept; deleteCircle() removes the row from the DB and refreshes $circles.
// $circles is passed directly as ComposeBox.targetCircles, so once deleted the
// circle pill simply disappears from the compose footer. No special filter logic
// is involved — the circle is just gone.

test('deleted circle does not appear in the compose circle picker', async ({
  page,
  seededTopic
}) => {
  await signInAsOwner(page, seededTopic.ownerMagic);
  await openCirclesTab(page);

  // Create a circle, then delete it.
  await page.getByPlaceholder('New circle name').fill('TempCircle');
  // Submit the create form via Enter on the name input. The "Add Circle"
  // button is sometimes pointer-intercepted by the scoped-title input on
  // narrower viewports, so we let the form's on:submit handler do the work.
  await page.getByPlaceholder('New circle name').press('Enter');
  await expect(page.locator('.circle-row strong', { hasText: 'TempCircle' })).toBeVisible();

  // Register dialog handler before clicking Delete.
  page.once('dialog', (dialog) => dialog.accept());

  const tempRow = page.locator('.circle-row').filter({
    has: page.locator('strong', { hasText: 'TempCircle' })
  });
  await tempRow.getByRole('button', { name: /^delete$/i }).click();
  await expect(page.locator('.circle-row strong', { hasText: 'TempCircle' })).toHaveCount(0);

  // Switch to the Updates tab. ComposeBox is rendered for moderators+.
  await page.getByRole('navigation').getByRole('button', { name: /^updates$/i }).click();
  await expect(page.getByPlaceholder('Write an update…')).toBeVisible();

  // The compose footer renders circle pills with class "circle-pill" for each
  // circle in targetCircles ($circles). TempCircle was hard-deleted so it must
  // not appear in the picker.
  await expect(
    page.locator('.circle-pills .circle-pill', { hasText: 'TempCircle' })
  ).toHaveCount(0);
});
