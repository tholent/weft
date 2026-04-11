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
// Case 1: Owner magic link → /manage/[token]
// Already covered by smoke.spec.ts — included here for completeness.
// ---------------------------------------------------------------------------

test('owner magic link redirects to manage', async ({ page, seededTopic }) => {
	await page.goto(`/auth?t=${seededTopic.ownerMagic}`);
	await page.waitForURL(/\/manage\/[^/]+/);
	expect(page.url()).toMatch(/\/manage\/[^/]+/);
});

// ---------------------------------------------------------------------------
// Case 2: Admin magic link → /manage/[token]
// ---------------------------------------------------------------------------

test('admin magic link redirects to manage', async ({ page, seededTopic }) => {
	const adminToken = Object.values(seededTopic.adminMagic)[0];
	await page.goto(`/auth?t=${adminToken}`);
	await page.waitForURL(/\/manage\/[^/]+/);
	expect(page.url()).toMatch(/\/manage\/[^/]+/);
});

// ---------------------------------------------------------------------------
// Case 3: Moderator magic link → /manage/[token]
// ---------------------------------------------------------------------------

test('moderator magic link redirects to manage', async ({ page, seededTopic }) => {
	const moderatorToken = Object.values(seededTopic.moderatorMagic)[0];
	await page.goto(`/auth?t=${moderatorToken}`);
	await page.waitForURL(/\/manage\/[^/]+/);
	expect(page.url()).toMatch(/\/manage\/[^/]+/);
});

// ---------------------------------------------------------------------------
// Case 4: Recipient magic link → /topic/[token]
// Already covered by smoke.spec.ts — included here for completeness.
// ---------------------------------------------------------------------------

test('recipient magic link redirects to topic', async ({ page, seededTopic }) => {
	const recipientToken = Object.values(seededTopic.recipientMagic)[0];
	await page.goto(`/auth?t=${recipientToken}`);
	await page.waitForURL(/\/topic\/[^/]+/);
	expect(page.url()).toMatch(/\/topic\/[^/]+/);
});

// ---------------------------------------------------------------------------
// Case 5: Invalid token → 401 from /auth/verify → client.ts redirect to /
//
// Note: client.ts intercepts every 401 by clearing localStorage and setting
// location.href = '/'. The auth route's `try/catch` never gets a chance to
// render its error UI for verify failures, so the visible behavior is a
// redirect to the landing page rather than the "Link error" heading.
// ---------------------------------------------------------------------------

test('invalid token redirects to landing page', async ({ page }) => {
	await page.goto('/auth?t=this-is-not-a-valid-signed-token');
	await page.waitForURL('http://127.0.0.1:4173/');
	await expect(page.getByRole('heading', { name: /^weft$/i })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Case 6: Missing token → error UI with "No token provided."
// ---------------------------------------------------------------------------

test('missing token shows no token provided error', async ({ page }) => {
	await page.goto('/auth');
	await expect(page.getByRole('heading', { name: /link error/i })).toBeVisible();
	await expect(page.getByText('No token provided.')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Case 7: Tampered token → 401 from /auth/verify → client.ts redirect to /
// Same caveat as Case 5: client.ts handles every 401 with a hard redirect.
// ---------------------------------------------------------------------------

test('tampered token redirects to landing page', async ({ page, seededTopic }) => {
	const real = seededTopic.ownerMagic;
	const mid = Math.floor(real.length / 2);
	// Flip one character: replace with 'X' unless it already is, then use 'Y'.
	const tampered = real.slice(0, mid) + (real[mid] === 'X' ? 'Y' : 'X') + real.slice(mid + 1);
	await page.goto(`/auth?t=${tampered}`);
	await page.waitForURL('http://127.0.0.1:4173/');
	await expect(page.getByRole('heading', { name: /^weft$/i })).toBeVisible();
});
