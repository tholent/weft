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

import { test, expect } from './support/fixtures';

// ---------------------------------------------------------------------------
// Helper: navigate to the Members tab as owner via seededTopic fixture.
// ---------------------------------------------------------------------------

async function goToMembersTab(page: import('@playwright/test').Page, magic: string) {
  await page.goto(`/auth?t=${magic}`);
  await page.waitForURL(/\/manage\//);
  // Wait for the manage page to fully load (skeleton resolves).
  await page.getByRole('button', { name: 'Members' }).click();
  // Wait for the members section heading to confirm the tab rendered.
  await expect(page.getByRole('heading', { name: 'Members' })).toBeVisible();
}

// ---------------------------------------------------------------------------
// Case 1: Owner invites a recipient by email.
// The InviteForm renders: channel-select (default email), email input,
// name input, circle select, role select, Invite button.
// After submit the component sets success = "Invite sent to <email>"
// and calls onInvited(member) which prepends the new member to the list.
// ---------------------------------------------------------------------------

test('owner invites a recipient by email', async ({ page, seededTopic }) => {
  await goToMembersTab(page, seededTopic.ownerMagic);

  // Channel defaults to email — the email input is already visible.
  await page.getByPlaceholder('Email address').fill('newrecipient@example.com');

  // Select the circle (the seed has exactly one circle: "Family").
  // The circle <select> is within .invite-form. Its first option is disabled
  // "Circle…"; the second is "Family".
  const circleSelect = page.locator('.invite-form select').nth(1);
  await circleSelect.selectOption({ label: 'Family' });

  // Role defaults to "recipient" — leave as-is.

  await page.getByRole('button', { name: 'Invite' }).click();

  // Success message from InviteForm: "Invite sent to newrecipient@example.com"
  await expect(page.locator('.invite-form .msg.ok')).toContainText('newrecipient@example.com');

  // The new member is appended to the list via onInvited; look for their email
  // in any member-row handle or the DOM text.
  await expect(page.getByText('newrecipient@example.com')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Case 2: Owner invites a moderator by phone (SMS channel).
// Switching the channel-select to "SMS" replaces the email input with a tel
// input (placeholder "Phone number").
// ---------------------------------------------------------------------------

test('owner invites a moderator by phone (SMS)', async ({ page, seededTopic }) => {
  await goToMembersTab(page, seededTopic.ownerMagic);

  // Switch channel to SMS.
  await page.locator('.channel-select').selectOption('sms');

  // The email input should be gone; the phone input should appear.
  await expect(page.getByPlaceholder('Phone number')).toBeVisible();
  await page.getByPlaceholder('Phone number').fill('+15550001234');

  // Select circle.
  const circleSelect = page.locator('.invite-form select').nth(1);
  await circleSelect.selectOption({ label: 'Family' });

  // Change role to moderator.
  const roleSelect = page.locator('.invite-form select').nth(2);
  await roleSelect.selectOption('moderator');

  await page.getByRole('button', { name: 'Invite' }).click();

  await expect(page.locator('.invite-form .msg.ok')).toContainText('+15550001234');
});

// ---------------------------------------------------------------------------
// Case 3: Admin role option is NOT present in the role dropdown when the
// viewer is an admin (not owner).  This is the client-side smoke of backend
// invariant #3: only the owner may grant admin privileges.
//
// InviteForm renders <option value="admin">Admin</option> only when $isOwner.
// An admin session must not see that option.
// ---------------------------------------------------------------------------

test('admin role option absent in InviteForm when viewer is admin', async ({
  page,
  seededTopic
}) => {
  // Sign in as the seeded admin.
  const adminMagic = seededTopic.adminMagic['admin@example.com'];
  await goToMembersTab(page, adminMagic);

  // The role dropdown is rendered inside .invite-form (only admins and owners
  // see the InviteForm at all; the template guards with {#if $isAdmin}).
  // Assert no <option value="admin"> exists.
  await expect(page.locator('.invite-form option[value="admin"]')).toHaveCount(0);

  // Sanity: the form itself IS rendered (admin can invite).
  await expect(page.locator('.invite-form')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Case 4: Resend invite.
// MemberRow renders a "Resend" button (class secondary-btn, text "Resend")
// for every member when canManage is true. Clicking it calls
// POST /topics/{id}/members/{memberId}/resend-invite.
// We use page.waitForResponse() to assert the request fires.
// ---------------------------------------------------------------------------

test('resend invite fires the correct API call', async ({ page, seededTopic }) => {
  await goToMembersTab(page, seededTopic.ownerMagic);

  // Wait for at least one member row to appear.
  await expect(page.locator('.member-row').first()).toBeVisible();

  // Set up response listener before clicking.
  const resendPromise = page.waitForResponse(
    (resp) => /resend-invite/.test(resp.url()) && resp.request().method() === 'POST'
  );

  // Click the first "Resend" button in the member list.
  await page.locator('.member-row .secondary-btn').first().click();

  const resendResp = await resendPromise;
  // The endpoint returns 200 or 204 on success.
  expect([200, 204]).toContain(resendResp.status());
});

// ---------------------------------------------------------------------------
// Case 5: Rename member.
// Only visible when viewerRole === 'owner'. The rename-btn (✎) toggles an
// inline text input; clicking Save calls renameMember() and updates the
// displayed handle.
// ---------------------------------------------------------------------------

test('owner can rename a member', async ({ page, seededTopic }) => {
  await goToMembersTab(page, seededTopic.ownerMagic);

  await expect(page.locator('.member-row').first()).toBeVisible();

  // Click the first rename button.
  const renameBtn = page.locator('.rename-btn').first();
  await expect(renameBtn).toBeVisible();
  await renameBtn.click();

  // An input field replaces the handle span; clear it and type a new handle.
  const handleInput = page.locator('.member-row input').first();
  await expect(handleInput).toBeVisible();
  await handleInput.fill('Renamed Member');

  // Click "Save" button that appears in the same row.
  await page.locator('.member-row button', { hasText: 'Save' }).first().click();

  // After renameMember() the component sets member.display_handle and hides
  // the input. The new name should be visible as a .handle span.
  await expect(page.locator('.handle', { hasText: 'Renamed Member' }).first()).toBeVisible();
});

// ---------------------------------------------------------------------------
// Case 6: Move member to a different circle.
// The seed has one circle ("Family"). To test move-member we need two circles.
// We use seedClient directly to create a topic with two circles.
// MemberRow renders a <select> that calls handleMove() on change.
// ---------------------------------------------------------------------------

test('move member fires the correct API call', async ({ page, seedClient }) => {
  await seedClient.reset();
  const seed = await seedClient.seedTopic({
    title: 'Move member test',
    owner_email: 'owner@example.com',
    owner_name: 'Owner',
    circles: [
      {
        name: 'Family',
        members: [{ email: 'alice@example.com', role: 'recipient', name: 'Alice' }]
      },
      {
        name: 'Friends',
        members: []
      }
    ]
  });

  await page.goto(`/auth?t=${seed.magic_links.owner}`);
  await page.waitForURL(/\/manage\//);
  await page.getByRole('button', { name: 'Members' }).click();
  await expect(page.getByRole('heading', { name: 'Members' })).toBeVisible();

  // Wait for member rows to load.
  await expect(page.locator('.member-row').first()).toBeVisible();

  // Listen for the move API call: PATCH /topics/{id}/members/{memberId}/circle
  const movePromise = page.waitForResponse(
    (resp) =>
      /\/members\/[^/]+\/circle/.test(resp.url()) && resp.request().method() === 'PATCH'
  );

  // The move-member select in MemberRow has option "Move to..." (disabled)
  // plus each circle. Select "Friends" for Alice's row.
  // Alice is a recipient, so the actions div is rendered (canManage = owner).
  const moveSelect = page.locator('.member-row .actions select').first();
  await moveSelect.selectOption({ label: 'Friends' });

  const moveResp = await movePromise;
  expect([200, 204]).toContain(moveResp.status());
});

// ---------------------------------------------------------------------------
// Case 7: retroactive_revoke checkbox is visible in the member row actions.
// MemberRow renders: <label class="retro"><input type="checkbox" bind:checked={retroactive} /> Retroactive</label>
// This is always present in the actions div when canManage is true and
// member.role !== 'owner'.
// ---------------------------------------------------------------------------

test('retroactive revoke checkbox is visible in member row', async ({ page, seededTopic }) => {
  await goToMembersTab(page, seededTopic.ownerMagic);

  // Wait for member rows.
  await expect(page.locator('.member-row').first()).toBeVisible();

  // The .retro label contains a checkbox with text "Retroactive".
  // At least one member row should have this checkbox visible.
  await expect(page.locator('.member-row .retro input[type="checkbox"]').first()).toBeVisible();
  await expect(page.locator('.member-row .retro').first()).toContainText('Retroactive');
});
