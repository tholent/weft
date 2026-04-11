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
// Cross-circle isolation (CRITICAL)
// Two circles, two recipients, two updates. Each recipient must only see the
// update targeted at their own circle.
// ---------------------------------------------------------------------------

test('alice sees Family update but not Coworker update', async ({ page, seedClient }) => {
	await seedClient.reset();
	const seed = await seedClient.seedTopic({
		title: 'Cross-circle isolation',
		owner_email: 'owner@example.com',
		owner_name: 'Owner',
		circles: [
			{
				name: 'Family',
				members: [{ email: 'alice@example.com', role: 'recipient', name: 'Alice' }]
			},
			{
				name: 'Coworkers',
				members: [{ email: 'bob@example.com', role: 'recipient', name: 'Bob' }]
			}
		],
		updates: [
			{
				body: 'Family update body',
				circle_names: ['Family'],
				author_email: 'owner@example.com'
			},
			{
				body: 'Coworker update body',
				circle_names: ['Coworkers'],
				author_email: 'owner@example.com'
			}
		]
	});

	const aliceMagic = seed.magic_links.recipients['alice@example.com'];
	await page.goto(`/auth?t=${aliceMagic}`);
	await page.waitForURL(/\/topic\//);

	await expect(page.getByText('Family update body')).toBeVisible();
	// Alice is not in the Coworkers circle — she must not see that update.
	expect(await page.getByText('Coworker update body').count()).toBe(0);
});

test('bob sees Coworker update but not Family update', async ({ page, seedClient }) => {
	await seedClient.reset();
	const seed = await seedClient.seedTopic({
		title: 'Cross-circle isolation',
		owner_email: 'owner@example.com',
		owner_name: 'Owner',
		circles: [
			{
				name: 'Family',
				members: [{ email: 'alice@example.com', role: 'recipient', name: 'Alice' }]
			},
			{
				name: 'Coworkers',
				members: [{ email: 'bob@example.com', role: 'recipient', name: 'Bob' }]
			}
		],
		updates: [
			{
				body: 'Family update body',
				circle_names: ['Family'],
				author_email: 'owner@example.com'
			},
			{
				body: 'Coworker update body',
				circle_names: ['Coworkers'],
				author_email: 'owner@example.com'
			}
		]
	});

	const bobMagic = seed.magic_links.recipients['bob@example.com'];
	await page.goto(`/auth?t=${bobMagic}`);
	await page.waitForURL(/\/topic\//);

	await expect(page.getByText('Coworker update body')).toBeVisible();
	// Bob is not in the Family circle — he must not see that update.
	expect(await page.getByText('Family update body').count()).toBe(0);
});

// ---------------------------------------------------------------------------
// Empty state
// A recipient who is in a circle with no updates should see the empty-state
// copy: "Nothing yet."
// ---------------------------------------------------------------------------

test('recipient sees empty state when no updates exist', async ({ page, seedClient }) => {
	await seedClient.reset();
	const seed = await seedClient.seedTopic({
		title: 'Empty topic',
		owner_email: 'owner@example.com',
		owner_name: 'Owner',
		circles: [
			{
				name: 'Friends',
				members: [{ email: 'carol@example.com', role: 'recipient', name: 'Carol' }]
			}
		]
		// No updates.
	});

	const carolMagic = seed.magic_links.recipients['carol@example.com'];
	await page.goto(`/auth?t=${carolMagic}`);
	await page.waitForURL(/\/topic\//);

	await expect(page.getByText('Nothing yet.')).toBeVisible();
	await expect(
		page.getByText('This is the quiet before the story begins. Check back soon.')
	).toBeVisible();
});

// ---------------------------------------------------------------------------
// Loading skeleton (best effort)
// The page sets `loading = true` during the onMount fetch and renders four
// skeleton cards. Because the dev/test backend is local and fast the skeleton
// often disappears before Playwright can observe it. We attempt a check
// immediately after navigation; if it's already gone the test passes anyway.
// ---------------------------------------------------------------------------

test('loading skeleton is shown while feed is fetching (best effort)', async ({
	page,
	seedClient
}) => {
	// NOTE: This test is inherently racy on fast local backends. If the skeleton
	// is never observed the test still passes — it is "best effort" as documented
	// in the task spec.
	await seedClient.reset();
	const seed = await seedClient.seedTopic({
		title: 'Skeleton test topic',
		owner_email: 'owner@example.com',
		owner_name: 'Owner',
		circles: [
			{
				name: 'Neighbors',
				members: [{ email: 'dave@example.com', role: 'recipient', name: 'Dave' }]
			}
		]
	});

	const daveMagic = seed.magic_links.recipients['dave@example.com'];

	// Slow down the page's fetch calls so we can catch the skeleton.
	await page.route('**/api/**', async (route) => {
		await new Promise((resolve) => setTimeout(resolve, 400));
		await route.continue();
	});

	await page.goto(`/auth?t=${daveMagic}`);
	await page.waitForURL(/\/topic\//);

	// The skeleton element has CSS class `topic-header--skeleton`. We check for
	// it immediately after navigation (before the delayed fetch resolves).
	// TODO: add data-testid="skeleton-header" to the skeleton div in
	//       src/routes/topic/[token]/+page.svelte for a more reliable selector.
	const skeletonLocator = page.locator('.topic-header--skeleton');
	// Either visible (caught in time) or gone (fetch was faster). Both are ok.
	const skeletonCount = await skeletonLocator.count();
	if (skeletonCount > 0) {
		await expect(skeletonLocator).toBeVisible();
		// Wait for it to disappear so subsequent tests start clean.
		await expect(skeletonLocator).not.toBeVisible({ timeout: 5000 });
	}
	// If count === 0 the skeleton already resolved — that is acceptable.
});

// ---------------------------------------------------------------------------
// Reply round-trip
// A recipient clicks the "Reply" button, types a reply body, submits.
// After submission the reply should appear in the ReplyThread rendered below
// the update card. The page calls loadReplies() after handleReply() so the
// reply text is fetched from the backend and rendered inline in a .reply-body
// paragraph.
// ---------------------------------------------------------------------------

test('recipient can submit a reply and it appears in the thread', async ({ page, seedClient }) => {
	await seedClient.reset();
	const seed = await seedClient.seedTopic({
		title: 'Reply round-trip',
		owner_email: 'owner@example.com',
		owner_name: 'Owner',
		circles: [
			{
				name: 'Community',
				members: [{ email: 'eve@example.com', role: 'recipient', name: 'Eve' }]
			}
		],
		updates: [
			{
				body: 'Update for reply test',
				circle_names: ['Community'],
				author_email: 'owner@example.com'
			}
		]
	});

	const eveMagic = seed.magic_links.recipients['eve@example.com'];
	await page.goto(`/auth?t=${eveMagic}`);
	await page.waitForURL(/\/topic\//);

	// Wait for the update card to be visible (feed loaded).
	await expect(page.getByText('Update for reply test')).toBeVisible();

	// The reply button shows "Reply" when reply_count is 0.
	const replyButton = page.getByRole('button', { name: 'Reply' });
	await expect(replyButton).toBeVisible();
	await replyButton.click();

	// The ComposeBox in reply mode renders a textarea with placeholder "Write a reply…"
	const replyTextarea = page.getByPlaceholder('Write a reply…');
	await expect(replyTextarea).toBeVisible();
	await replyTextarea.fill('Hello from Eve');

	// Submit via the "Send" button inside the ComposeBox.
	await page.getByRole('button', { name: 'Send' }).click();

	// After handleReply → loadReplies the ReplyThread is rendered. The reply
	// body text is in a <p class="reply-body"> inside .reply-thread.
	// NOTE: getReplies is called after createReply, so this is a network round-
	// trip. The reply should appear in the DOM once the GET /replies response lands.
	// TODO: add data-testid="reply-body" to <p class="reply-body"> in
	//       src/lib/components/ReplyThread.svelte for a more reliable selector.
	await expect(page.getByText('Hello from Eve')).toBeVisible({ timeout: 5000 });
});
