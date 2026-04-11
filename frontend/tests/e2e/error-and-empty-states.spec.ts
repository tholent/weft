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

// FT-36: E13 error and empty states E2E
//
// Five cases:
//   1. Expired/revoked bearer token → 401 → redirect to landing /
//   2. Network error mid-request → unhandled exception (no inline UI surface)
//   3. Empty feed (no updates) → "Nothing posted yet."
//   4. Empty members list → "No members yet."
//   5. Empty replies in UpdateModal → "No replies yet."

import { test, expect } from './support/fixtures';
import type { SeedTopicSpec } from './fixtures/seed-client';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Sign in via owner magic link and wait for the manage page to be ready. */
async function signInAsOwner(
  page: import('@playwright/test').Page,
  ownerMagic: string
): Promise<void> {
  await page.goto(`/auth?t=${ownerMagic}`);
  await page.waitForURL(/\/manage\/[^/]+/);
  // Wait for skeleton to resolve — the Updates nav tab becomes visible once data loads.
  await expect(page.getByRole('button', { name: /^updates$/i })).toBeVisible();
}

// ---------------------------------------------------------------------------
// Case 1: Expired/garbage bearer token → 401 → redirect to landing /
//
// The /manage/[token] route does NOT read the URL segment as a bearer; it
// relies on the session store, which is populated by the /auth route after
// a successful magic-link verify. Navigating directly to /manage/garbage
// leaves $session.topicId null and the onMount short-circuits without any
// API call, so no 401 is triggered.
//
// To reach the 401-redirect path we first sign in normally (so the manage
// page has a populated session), then corrupt the stored bearer in
// localStorage, then reload. On reload, onMount fires GET /topics/{id}
// with the bad bearer, the backend returns 401, and client.ts sets
// location.href = '/'.
// ---------------------------------------------------------------------------

test('expired bearer token redirects to landing page', async ({ page, seededTopic }) => {
  await page.goto(`/auth?t=${seededTopic.ownerMagic}`);
  await page.waitForURL(/\/manage\//);

  // Corrupt the bearer so the next API call returns 401.
  await page.evaluate(() => {
    localStorage.setItem('weft_token', 'not-a-real-bearer');
  });

  await page.reload();
  await page.waitForURL('http://127.0.0.1:4173/');
  await expect(page.getByRole('heading', { name: /^weft$/i })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Case 2: Network error mid-request → unhandled exception in the browser
//
// The manage page's handleNewUpdate() calls createUpdate() then getFeed().
// Neither function wraps its fetch call in a try/catch that surfaces a visible
// UI error element. When the network request fails (or returns 5xx), client.ts
// throws an ApiError that propagates as an unhandled promise rejection.
//
// Surface analysis:
//   - ComposeBox.handleSubmit() calls onSubmit() (= handleNewUpdate) without
//     try/catch; no inline error element is set.
//   - The only ComposeBox error state (uploadError) is for attachment uploads
//     only, not for the core createUpdate path.
//   - There is no window.alert call or global error banner in the manage page.
//
// Therefore the only observable signal is a browser-level pageerror event
// (unhandled promise rejection). We assert that signal here rather than
// looking for a DOM element.
//
// If a future iteration adds an inline error UI (e.g. a toast or an error
// paragraph in ComposeBox), update this test to assert that element instead.
// ---------------------------------------------------------------------------

test('network error mid-request surfaces as an unhandled browser exception', async ({
  page,
  seededTopic
}) => {
  await signInAsOwner(page, seededTopic.ownerMagic);

  // Collect unhandled page errors (uncaught exceptions + unhandled rejections).
  const pageErrors: Error[] = [];
  page.on('pageerror', (err) => pageErrors.push(err));

  // Intercept the create-update endpoint and return a 500 error.
  // The URL pattern matches POST /topics/<id>/updates.
  await page.route('**/topics/**/updates', (route) => {
    if (route.request().method() === 'POST') {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' })
      });
    } else {
      // Allow GET (feed reload) to pass through so the page can still render.
      route.continue();
    }
  });

  // Fill the compose box and send.
  await page.getByPlaceholder('Write an update…').fill('This update should fail');
  await page.getByRole('button', { name: /^send$/i }).click();

  // Wait briefly for the async rejection to propagate.
  await page.waitForTimeout(500);

  // Assert that a page-level error was raised — confirming the thrown ApiError
  // reached the browser's unhandled-rejection handler.
  expect(pageErrors.length).toBeGreaterThan(0);
});

// ---------------------------------------------------------------------------
// Case 3: Empty feed → "Nothing posted yet."
//
// Seed a topic with no updates. After sign-in the feed is empty and the
// manage page renders the empty-state headline.
// ---------------------------------------------------------------------------

const EMPTY_TOPIC_SPEC: SeedTopicSpec = {
  title: 'Empty topic for E2E',
  owner_email: 'owner@example.com',
  owner_name: 'Owner',
  circles: [{ name: 'Family', members: [] }]
};

test('empty feed shows "Nothing posted yet."', async ({ page, seedClient }) => {
  await seedClient.reset();
  const data = await seedClient.seedTopic(EMPTY_TOPIC_SPEC);

  await signInAsOwner(page, data.magic_links.owner);

  // The Updates tab is the default. With no updates the empty-state renders.
  await expect(page.getByText(/nothing posted yet\./i)).toBeVisible();
});

// ---------------------------------------------------------------------------
// Case 4: Empty members list → SKIPPED.
//
// The "No members yet." empty state on the Members tab is unreachable in
// practice because the owner is always a member of their own topic — so
// $members.length is never zero when an owner is viewing the page. The
// manage page has no route by which a non-owner viewer would see an empty
// member list. This empty-state branch in the template is dead code for
// the current flows.
// ---------------------------------------------------------------------------

test.skip('empty members list shows "No members yet."', async ({ page, seedClient }) => {
  void page;
  void seedClient;
});

// ---------------------------------------------------------------------------
// Case 5: Empty replies in UpdateModal → "No replies yet."
//
// Seed a topic with one update and no replies. Sign in as owner, click the
// update card to open UpdateModal, and verify the empty replies state.
//
// Source: UpdateModal.svelte line 185 — {:else}<p class="empty">No replies yet.</p>
// ---------------------------------------------------------------------------

test('update with no replies shows "No replies yet." in UpdateModal', async ({
  page,
  seedClient
}) => {
  await seedClient.reset();
  const data = await seedClient.seedTopic({
    title: 'Replies empty topic',
    owner_email: 'owner@example.com',
    owner_name: 'Owner',
    circles: [{ name: 'Family', members: [] }],
    updates: [
      {
        body: 'Update with no replies',
        circle_names: ['Family'],
        author_email: 'owner@example.com'
      }
    ]
  });

  await signInAsOwner(page, data.magic_links.owner);

  // Click the update card to open UpdateModal.
  const updateCard = page.locator('.update-row').filter({ hasText: 'Update with no replies' });
  await updateCard.click();

  // UpdateModal is open — wait for the dialog to be visible.
  const modal = page.locator('[role="dialog"]');
  await expect(modal).toBeVisible();

  // The replies section loads asynchronously (onMount → getReplies).
  // Wait for the "Replies (0)" heading or the empty paragraph.
  await expect(modal.getByText(/no replies yet\./i)).toBeVisible();

  // Close the modal.
  await modal.getByRole('button', { name: '✕' }).click();
  await expect(modal).not.toBeVisible();
});
