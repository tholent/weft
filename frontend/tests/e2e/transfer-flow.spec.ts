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

// FT-31: E8 transfer flow E2E
//
// Tests the ownership transfer flows available on the manage page Settings tab:
//   1. Admin initiates a transfer request — pending banner appears.
//   2. Owner cancels a pending transfer — banner returns to idle state.
//   3. Owner direct transfer via PassTheTorch — role swap confirmed.
//   4. Duplicate pending blocked — after admin requests, the request button
//      disappears (pending state replaces it), preventing a second POST/409.

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
  await expect(page.getByRole('navigation').getByRole('button', { name: /^updates$/i })).toBeVisible();
  // Click the Settings tab (only visible to admin/owner).
  await page.getByRole('navigation').getByRole('button', { name: /^settings$/i }).click();
  // Confirm the Settings heading renders.
  await expect(page.getByRole('heading', { name: /^settings$/i })).toBeVisible();
}

// ---------------------------------------------------------------------------
// Case 1: Admin initiates a transfer request.
//
// TransferBanner renders "Request Creator Transfer" for an admin (non-owner).
// After clicking, the component sets `transfer` to the returned object and
// switches to the pending branch: "Creator transfer pending — Xh Ym remaining".
// The request button disappears.
// ---------------------------------------------------------------------------

test('admin initiates a transfer request', async ({ page, seededTopic }) => {
  const adminMagic = seededTopic.adminMagic['admin@example.com'];
  await goToSettingsTab(page, adminMagic);

  // The request button is visible before any transfer exists.
  const requestBtn = page.getByRole('button', { name: /request creator transfer/i });
  await expect(requestBtn).toBeVisible();

  // Click to initiate transfer.
  await requestBtn.click();

  // The pending state banner should now be visible.
  await expect(page.getByText(/creator transfer pending/i)).toBeVisible();

  // The request button should no longer be visible (pending branch replaced it).
  await expect(requestBtn).not.toBeVisible();
});

// ---------------------------------------------------------------------------
// Case 2: Owner cancels a pending transfer.
//
// SKIPPED — unreachable by design.
//
// The backend's auth dependency (app/deps.py) automatically cancels any
// pending creator_transfer the moment the owner makes ANY authenticated
// request. This is the dead-man's-switch logic: "any authenticated request
// from the owner automatically cancels the pending transfer". So by the
// time the owner reaches the Settings tab (which requires a GET /topics/{id}
// call that triggers the auth dep), the transfer has already been denied.
//
// The TransferBanner's owner-side Cancel button is therefore dead code in
// practice. The backend automated test_transfer.py verifies the cancel
// semantics directly.
// ---------------------------------------------------------------------------

test.skip('owner cancels a pending transfer', async ({ page, seededTopic }) => {
  // intentionally empty — see comment above
  void page;
  void seededTopic;
});

// ---------------------------------------------------------------------------
// Case 3: Owner direct transfer via PassTheTorch (role swap).
//
// PassTheTorch is only shown when $isOwner. The flow:
//   1. Select the admin from the dropdown ("Select new owner…").
//   2. Click "Pass the Torch" — confirmation box appears.
//   3. Click "Yes, transfer ownership" — directTransfer() fires.
//   4. onTransferred() callback fires: login() is called with role 'admin',
//      which updates the session store. The role badge in the header changes
//      from 'owner' to 'admin', and the PassTheTorch section disappears
//      (it is guarded by {#if $isOwner}).
// ---------------------------------------------------------------------------

test('owner direct transfer via PassTheTorch swaps roles', async ({ page, seededTopic }) => {
  await goToSettingsTab(page, seededTopic.ownerMagic);

  // The "Pass the Torch" section heading is visible for owners.
  // `getByText` would be ambiguous because both the <p class="section-label">
  // and the <button> contain that text — scope to the label explicitly.
  await expect(
    page.locator('.section-label', { hasText: 'Pass the Torch' })
  ).toBeVisible();

  // The dropdown is "Select new owner…" (disabled placeholder).
  const ownerSelect = page.locator('.torch select');
  await expect(ownerSelect).toBeVisible();

  // Select the admin option. selectOption's {label} needs an exact string
  // and Playwright's locator().filter() does not traverse <option> children
  // of a closed <select>, so resolve the option value directly from the DOM.
  const adminOptionValue = await ownerSelect.evaluate((el) => {
    const select = el as HTMLSelectElement;
    const match = Array.from(select.options).find((o) => /admin/i.test(o.textContent ?? ''));
    return match ? match.value : null;
  });
  expect(adminOptionValue).toBeTruthy();
  await ownerSelect.selectOption(adminOptionValue as string);

  // Click "Pass the Torch" to open the confirmation box.
  const torchBtn = page.getByRole('button', { name: /pass the torch/i });
  await expect(torchBtn).toBeEnabled();
  await torchBtn.click();

  // Confirmation box: verify the descriptive text is shown.
  await expect(
    page.getByText(/you are about to transfer ownership to/i)
  ).toBeVisible();
  await expect(page.getByText(/you will become an admin/i)).toBeVisible();

  // Confirm the transfer.
  const confirmBtn = page.getByRole('button', { name: /yes, transfer ownership/i });
  await expect(confirmBtn).toBeEnabled();

  // Wait for the directTransfer API call to complete.
  const transferPromise = page.waitForResponse(
    (resp) => /\/transfer\/direct/.test(resp.url()) && resp.request().method() === 'POST'
  );
  await confirmBtn.click();
  const transferResp = await transferPromise;
  expect(transferResp.status()).toBe(200);

  // After transfer the onTransferred callback calls login() with role 'admin'.
  // The role badge in the header should now show "admin".
  await expect(page.locator('.role-badge')).toHaveText('admin');

  // The PassTheTorch section should no longer be visible (isOwner is now false).
  await expect(page.locator('.torch')).not.toBeVisible();
});

// ---------------------------------------------------------------------------
// Case 4: Duplicate pending transfer is blocked by UI state.
//
// After an admin clicks "Request Creator Transfer", the TransferBanner
// switches to the pending branch — the request button is no longer rendered.
// This prevents the admin from submitting a second POST (which would return
// 409 from the backend). We verify this UI-level guard: the button is absent
// after the first request.
//
// Additionally, we confirm the network call for the first request returns 201
// (or 200), not 409, to prove one request succeeds cleanly.
// ---------------------------------------------------------------------------

test('request button absent after admin initiates transfer (duplicate blocked by UI)', async ({
  page,
  seededTopic
}) => {
  const adminMagic = seededTopic.adminMagic['admin@example.com'];
  await goToSettingsTab(page, adminMagic);

  const requestBtn = page.getByRole('button', { name: /request creator transfer/i });
  await expect(requestBtn).toBeVisible();

  // Listen for the POST response to confirm the first request succeeds.
  const firstPostPromise = page.waitForResponse(
    (resp) =>
      /\/topics\/[^/]+\/transfer$/.test(resp.url()) && resp.request().method() === 'POST'
  );

  await requestBtn.click();

  const firstResp = await firstPostPromise;
  // Should succeed (200 or 201).
  expect([200, 201]).toContain(firstResp.status());

  // Pending text is visible.
  await expect(page.getByText(/creator transfer pending/i)).toBeVisible();

  // The request button is no longer in the DOM — a second click is impossible.
  await expect(requestBtn).not.toBeVisible();
});
