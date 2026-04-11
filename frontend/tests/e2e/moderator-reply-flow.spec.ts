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

/**
 * FT-28: E5 — moderator reply/relay/respond E2E
 *
 * This suite covers the moderator-facing reply moderation surface:
 *
 *   Case 1 — Recipient posts a shareable reply.
 *   Case 2 — Moderator approves (relays) a pending reply.
 *   Case 3 — Moderator dismisses a pending reply (and can undo).
 *   Case 4 — Mod-response form. [SKIPPED — not in the UI surface]
 *
 * Implementation notes:
 *
 *   - The UpdateModal (manage page) is opened by clicking an UpdateCard row.
 *     It loads replies via GET on mount, then renders a ReplyThread that shows
 *     "Approve" / "Dismiss" buttons for pending replies when isModerator=true.
 *   - There is NO mod-response submission form anywhere in the current source.
 *     ReplyThread shows existing mod_responses as read-only text. UpdateModal
 *     has a "Reply" compose area for moderators that posts a regular reply via
 *     createReply() — it does NOT create a mod response. Case 4 is therefore
 *     untestable through the UI and is marked as skipped with an explanation.
 *   - The recipient topic page (src/routes/topic/[token]/+page.svelte) renders
 *     ReplyThread with isModerator=false, so no relay/dismiss buttons appear
 *     there. That is correct behaviour.
 */

import type { Page } from '@playwright/test';
import { test, expect } from './support/fixtures';

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/**
 * Sign in via a magic-link token and wait for the redirect to complete.
 */
async function signIn(page: Page, token: string, expectedRoute: RegExp) {
	await page.goto(`/auth?t=${token}`);
	await page.waitForURL(expectedRoute);
}

// ---------------------------------------------------------------------------
// Case 1: Recipient posts a shareable reply
//
// Alice submits a reply through the recipient view (topic/[token]) and checks
// the "Share with group" checkbox before hitting Send.  After submission the
// reply body must appear in the thread rendered below the update card.
// ---------------------------------------------------------------------------

test('recipient posts a shareable reply and it appears in the thread', async ({
	page,
	seedClient
}) => {
	await seedClient.reset();
	const seed = await seedClient.seedTopic({
		title: 'Shareable reply test',
		owner_email: 'owner@example.com',
		owner_name: 'Owner',
		circles: [
			{
				name: 'Family',
				members: [{ email: 'alice@example.com', role: 'recipient', name: 'Alice' }]
			}
		],
		updates: [
			{
				body: 'Update to reply to',
				circle_names: ['Family'],
				author_email: 'owner@example.com'
			}
		]
	});

	const aliceMagic = seed.magic_links.recipients['alice@example.com'];
	await signIn(page, aliceMagic, /\/topic\//);

	// Wait for the update to load.
	await expect(page.getByText('Update to reply to')).toBeVisible();

	// Click the "Reply" button to reveal the ComposeBox.
	const replyButton = page.getByRole('button', { name: 'Reply' });
	await expect(replyButton).toBeVisible();
	await replyButton.click();

	// Fill the reply body in the ComposeBox (placeholder: "Write a reply…").
	const replyTextarea = page.getByPlaceholder('Write a reply…');
	await expect(replyTextarea).toBeVisible();
	await replyTextarea.fill('This is Alice sharing with the group');

	// Check the "Share with group" checkbox that maps to wants_to_share.
	const shareCheckbox = page.getByLabel('Share with group');
	await expect(shareCheckbox).toBeVisible();
	await shareCheckbox.check();
	await expect(shareCheckbox).toBeChecked();

	// Submit via the "Send" button.
	await page.getByRole('button', { name: 'Send' }).click();

	// After submission the page calls loadReplies() → GET /replies, and the
	// result is rendered in a <p class="reply-body"> inside .reply-thread.
	await expect(page.getByText('This is Alice sharing with the group')).toBeVisible({
		timeout: 5000
	});
});

// ---------------------------------------------------------------------------
// Case 2: Moderator relays (approves) a pending reply
//
// We seed the reply via seedClient directly (no need to drive Alice through
// the UI again) then sign in as mod and exercise the Approve button in the
// UpdateModal.
// ---------------------------------------------------------------------------

test('moderator approves a pending reply and Approve button disappears', async ({
	page,
	seedClient
}) => {
	await seedClient.reset();
	const seed = await seedClient.seedTopic({
		title: 'Relay reply test',
		owner_email: 'owner@example.com',
		owner_name: 'Owner',
		circles: [
			{
				name: 'Family',
				members: [
					{ email: 'alice@example.com', role: 'recipient', name: 'Alice' },
					{ email: 'mod@example.com', role: 'moderator', name: 'Mod User' }
				]
			}
		],
		updates: [
			{
				body: 'Update with a pending reply',
				circle_names: ['Family'],
				author_email: 'owner@example.com'
			}
		],
		replies: [
			{
				update_index: 0,
				author_email: 'alice@example.com',
				body: 'Alice pending reply for relay'
			}
		]
	});

	const modMagic = seed.magic_links.moderators['mod@example.com'];
	await signIn(page, modMagic, /\/manage\//);

	// The Updates tab is active by default. Click the update card to open the
	// UpdateModal (the whole .update-row is clickable via the onClick prop).
	await expect(page.getByText('Update with a pending reply')).toBeVisible();
	await page.getByText('Update with a pending reply').click();

	// The UpdateModal loads replies on mount. Wait for the reply body.
	await expect(page.getByText('Alice pending reply for relay')).toBeVisible({ timeout: 5000 });

	// A pending reply shows an "Approve" button (class="action approve") when
	// viewed by a moderator (ReplyThread.svelte line 50).
	const approveButton = page.getByRole('button', { name: 'Approve' });
	await expect(approveButton).toBeVisible();
	await approveButton.click();

	// After relay the component refreshes replies from the server.  The reply
	// status transitions from "pending" → "relayed", so the Approve button must
	// disappear and a "relayed" status badge must appear.
	await expect(approveButton).not.toBeVisible({ timeout: 5000 });
	await expect(page.getByText('relayed')).toBeVisible({ timeout: 5000 });
});

// ---------------------------------------------------------------------------
// Case 3: Moderator dismisses a reply and can undo
//
// Seed TWO replies.  Dismiss the second one and verify:
//   a) The Dismiss button disappears for that reply.
//   b) A "dismissed" badge appears.
//   c) An "Undo" button appears (ReplyThread.svelte line 55).
//   d) Clicking Undo transitions the reply back to "relayed".
// The first reply is left untouched to confirm independent state.
// ---------------------------------------------------------------------------

test('moderator dismisses a reply and can undo it', async ({ page, seedClient }) => {
	await seedClient.reset();
	const seed = await seedClient.seedTopic({
		title: 'Dismiss reply test',
		owner_email: 'owner@example.com',
		owner_name: 'Owner',
		circles: [
			{
				name: 'Family',
				members: [
					{ email: 'alice@example.com', role: 'recipient', name: 'Alice' },
					{ email: 'bob@example.com', role: 'recipient', name: 'Bob' },
					{ email: 'mod@example.com', role: 'moderator', name: 'Mod User' }
				]
			}
		],
		updates: [
			{
				body: 'Update with two pending replies',
				circle_names: ['Family'],
				author_email: 'owner@example.com'
			}
		],
		replies: [
			{
				update_index: 0,
				author_email: 'alice@example.com',
				body: 'Alice reply — keep this one'
			},
			{
				update_index: 0,
				author_email: 'bob@example.com',
				body: 'Bob reply — dismiss this one'
			}
		]
	});

	const modMagic = seed.magic_links.moderators['mod@example.com'];
	await signIn(page, modMagic, /\/manage\//);

	// Open the UpdateModal.
	await expect(page.getByText('Update with two pending replies')).toBeVisible();
	await page.getByText('Update with two pending replies').click();

	// Both replies must be visible.
	await expect(page.getByText('Alice reply — keep this one')).toBeVisible({ timeout: 5000 });
	await expect(page.getByText('Bob reply — dismiss this one')).toBeVisible({ timeout: 5000 });

	// Two "Dismiss" buttons are rendered (one per pending reply).
	// We target the one adjacent to Bob's reply by using a locator scoped to the
	// reply container.  ReplyThread renders each reply in a <div class="reply">.
	// The reply with Bob's text contains a Dismiss button.
	const bobReplyContainer = page.locator('.reply', { hasText: 'Bob reply — dismiss this one' });
	const dismissButton = bobReplyContainer.getByRole('button', { name: 'Dismiss' });
	await expect(dismissButton).toBeVisible();
	await dismissButton.click();

	// Dismiss button disappears, "dismissed" badge appears, "Undo" button appears.
	await expect(dismissButton).not.toBeVisible({ timeout: 5000 });
	await expect(bobReplyContainer.getByText('dismissed')).toBeVisible({ timeout: 5000 });

	const undoButton = bobReplyContainer.getByRole('button', { name: 'Undo' });
	await expect(undoButton).toBeVisible();

	// Alice's reply is still pending — her Approve/Dismiss buttons still present.
	const aliceReplyContainer = page.locator('.reply', { hasText: 'Alice reply — keep this one' });
	await expect(aliceReplyContainer.getByRole('button', { name: 'Dismiss' })).toBeVisible();

	// Click Undo — this calls relay() on the dismissed reply, which transitions
	// it from "dismissed" → "relayed" (ReplyThread.svelte line 55: undo calls relay).
	await undoButton.click();
	await expect(undoButton).not.toBeVisible({ timeout: 5000 });
	// After undo the reply is relayed; a "relayed" badge is expected.
	await expect(bobReplyContainer.getByText('relayed')).toBeVisible({ timeout: 5000 });
});

// ---------------------------------------------------------------------------
// Case 4: Moderator posts a mod response with sender_circle scope
//
// SKIPPED — there is no mod-response submission form in the current UI.
//
// Audit of source files confirms:
//   - ReplyThread.svelte (src/lib/components/ReplyThread.svelte):
//     Renders existing mod_responses as display-only text inside
//     <div class="mod-responses">. There is no form, textarea, or submit
//     button for creating a new mod response.
//   - UpdateModal.svelte (src/lib/components/UpdateModal.svelte):
//     Has a "Reply" compose area for moderators that calls createReply()
//     (src/lib/api/replies.ts). This creates a normal reply, NOT a mod
//     response. The modal has no separate "mod response" form.
//   - manage/[token]/+page.svelte: No mod-response form outside the modal.
//   - No other component or route file contains a mod-response creation form.
//
// The backend API almost certainly supports POST /replies/:id/mod_response (or
// similar), but the frontend has not yet implemented a UI surface for it.
// When the form is added, this test should be implemented as follows:
//
//   1. Seed a topic with a relayed reply.
//   2. Sign in as moderator, open the UpdateModal.
//   3. Find the mod-response form adjacent to the relayed reply.
//   4. Fill body, select scope ("sender_circle"), submit.
//   5. Assert the mod response text appears in the .mod-responses container.
// ---------------------------------------------------------------------------

test.skip('moderator posts a mod response — UI not yet implemented', async () => {
	// See block comment above. Remove .skip when the mod-response form lands.
});
