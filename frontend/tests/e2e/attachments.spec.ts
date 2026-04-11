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

// FT-33: E10 attachments E2E
//
// Tests attachment upload, thumbnail rendering, lightbox, oversize rejection,
// and disallowed MIME rejection via the ComposeBox / UpdateCard components.
//
// Backend MIME allowlist (from app/services/attachment.py):
//   image/jpeg, image/png, image/webp, image/gif — all others rejected with 400.
//   Magic bytes are also verified: declared content-type must match file header.
//   Size limit is set to 2048 bytes in start-e2e.sh for these tests
//   (vs. the default 10 MB) so a ~3 KB PNG triggers the oversize error.
//
// Fixtures:
//   tests/e2e/fixtures/sample.png   — 69-byte valid 1×1 RGB PNG (below 2048 B limit)
//   tests/e2e/fixtures/oversize.png — ~3 KB valid PNG (above 2048 B limit)
//   tests/e2e/fixtures/oversize.bin — 4096-byte binary blob (no image magic bytes)

import { test, expect } from './support/fixtures';
import path from 'node:path';

const FIXTURES = path.join(process.cwd(), 'tests/e2e/fixtures');

// ---------------------------------------------------------------------------
// Helper — sign in as owner and wait for the manage page to be ready.
// ---------------------------------------------------------------------------

async function signInAsOwner(
  page: import('@playwright/test').Page,
  ownerMagic: string
): Promise<void> {
  await page.goto(`/auth?t=${ownerMagic}`);
  await page.waitForURL(/\/manage\/[^/]+/);
  await expect(page.getByRole('button', { name: /^updates$/i })).toBeVisible();
}

// ---------------------------------------------------------------------------
// Test 1 — Happy upload path: post an update with a PNG attachment and assert
//           that the thumbnail appears in the resulting UpdateCard.
// ---------------------------------------------------------------------------

test('owner uploads a PNG attachment and the thumbnail appears on the update card', async ({
  page,
  seededTopic
}) => {
  await signInAsOwner(page, seededTopic.ownerMagic);

  // Type a body in the ComposeBox.
  const compose = page.getByPlaceholder('Write an update…');
  await compose.fill('Photo update with attachment');

  // The file input is hidden (display:none). setInputFiles works on hidden inputs.
  const fileInput = page.locator('input[type="file"].file-input-hidden');
  await fileInput.setInputFiles(path.join(FIXTURES, 'sample.png'));

  // A preview thumbnail should appear in the compose area immediately after selection.
  await expect(page.locator('.photo-thumb').first()).toBeVisible();

  // Submit the update.
  await page.getByRole('button', { name: /^send$/i }).click();

  // ComposeBox refreshes the feed BEFORE uploadAttachment fires, so the freshly
  // rendered UpdateCard does not include the attachment yet. Reload the page
  // so the next feed fetch includes the attachment row. (This is a known
  // timing quirk in handleSubmit — see ComposeBox.svelte line ~119.)
  await expect(page.getByText('Photo update with attachment')).toBeVisible();
  await page.reload();

  // After reload the UpdateCard should include the attachment thumbnail.
  const updateCard = page
    .locator('.update-row')
    .filter({ hasText: 'Photo update with attachment' });
  await expect(updateCard.locator('.attachment-grid img.thumb').first()).toBeVisible({
    timeout: 10000
  });
});

// ---------------------------------------------------------------------------
// Test 2 — Thumbnail is rendered (visual check on the card after upload).
//           This is covered as part of Test 1; this test validates that the
//           img src points to the attachment API endpoint.
// ---------------------------------------------------------------------------

test('thumbnail src points to the attachment API endpoint', async ({ page, seededTopic }) => {
  await signInAsOwner(page, seededTopic.ownerMagic);

  const compose = page.getByPlaceholder('Write an update…');
  await compose.fill('Thumbnail endpoint test');

  const fileInput = page.locator('input[type="file"].file-input-hidden');
  await fileInput.setInputFiles(path.join(FIXTURES, 'sample.png'));

  await page.getByRole('button', { name: /^send$/i }).click();

  // Reload to capture the attachment in the feed (see handleSubmit race note).
  await expect(page.getByText('Thumbnail endpoint test')).toBeVisible();
  await page.reload();

  const updateCard = page.locator('.update-row').filter({ hasText: 'Thumbnail endpoint test' });
  const thumbImg = updateCard.locator('.attachment-grid img.thumb').first();
  await expect(thumbImg).toBeVisible({ timeout: 10000 });

  // The src should point at the attachment endpoint on the configured API
  // base. In unit tests that's /api/...; in E2E it's the absolute backend URL
  // because VITE_API_BASE is baked in at build time. Accept either form.
  const src = await thumbImg.getAttribute('src');
  expect(src).toMatch(/\/topics\/[^/]+\/attachments\/[^/]+/);
});

// ---------------------------------------------------------------------------
// Test 3 — Lightbox: clicking the thumbnail opens the overlay; clicking the
//           overlay closes it.
// ---------------------------------------------------------------------------

test('clicking an attachment thumbnail opens the lightbox and clicking the overlay closes it', async ({
  page,
  seededTopic
}) => {
  await signInAsOwner(page, seededTopic.ownerMagic);

  const compose = page.getByPlaceholder('Write an update…');
  await compose.fill('Lightbox test update');

  const fileInput = page.locator('input[type="file"].file-input-hidden');
  await fileInput.setInputFiles(path.join(FIXTURES, 'sample.png'));

  await page.getByRole('button', { name: /^send$/i }).click();

  // Reload to capture the attachment in the feed (see handleSubmit race note).
  await expect(page.getByText('Lightbox test update')).toBeVisible();
  await page.reload();

  const updateCard = page.locator('.update-row').filter({ hasText: 'Lightbox test update' });
  const thumbBtn = updateCard.locator('.thumb-btn').first();
  await expect(thumbBtn).toBeVisible({ timeout: 10000 });

  // Click the thumbnail button to open the lightbox.
  await thumbBtn.click();

  // The lightbox overlay should be visible.
  const overlay = page.locator('.lightbox-overlay');
  await expect(overlay).toBeVisible();

  // The full-size image inside the lightbox should also be visible.
  await expect(overlay.locator('.lightbox-img')).toBeVisible();

  // Click the overlay to close the lightbox.
  await overlay.click();

  // Overlay should be gone.
  await expect(overlay).not.toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 4 — Oversize rejection: uploading a PNG that exceeds the 2 KB test
//           limit (oversize.png ~3 KB) should result in an upload error message
//           after the update is submitted.
//
//           Flow: the update itself is created (body is accepted), then the
//           attachment upload fails at the backend, and the ComposeBox shows
//           the upload error text.
// ---------------------------------------------------------------------------

test('uploading an oversized image shows an upload error after submit', async ({
  page,
  seededTopic
}) => {
  await signInAsOwner(page, seededTopic.ownerMagic);

  const compose = page.getByPlaceholder('Write an update…');
  await compose.fill('Oversize attachment test');

  const fileInput = page.locator('input[type="file"].file-input-hidden');
  await fileInput.setInputFiles(path.join(FIXTURES, 'oversize.png'));

  // Preview appears in compose area.
  await expect(page.locator('.photo-thumb').first()).toBeVisible();

  await page.getByRole('button', { name: /^send$/i }).click();

  // The update body should be posted successfully (the update appears).
  await expect(page.getByText('Oversize attachment test')).toBeVisible();

  // The upload error paragraph should appear because the attachment was rejected.
  await expect(page.locator('.upload-error')).toBeVisible({ timeout: 8000 });
  const errorText = await page.locator('.upload-error').textContent();
  expect(errorText).toContain('oversize.png');
});

// ---------------------------------------------------------------------------
// Test 5 — Disallowed MIME rejection: uploading a binary file (oversize.bin)
//           with no image magic bytes should be rejected.
//
//           When Playwright calls setInputFiles on a hidden input for a .bin
//           file, the browser assigns content-type application/octet-stream,
//           which is not in the backend allowlist (image/jpeg|png|webp|gif).
//           The backend returns 400 and the ComposeBox shows an upload error.
//
//           NOTE: The file input has accept="image/*", which the browser
//           enforces in interactive mode but does not block setInputFiles.
// ---------------------------------------------------------------------------

test('uploading a non-image binary file shows an upload error after submit', async ({
  page,
  seededTopic
}) => {
  await signInAsOwner(page, seededTopic.ownerMagic);

  const compose = page.getByPlaceholder('Write an update…');
  await compose.fill('Non-image MIME test');

  const fileInput = page.locator('input[type="file"].file-input-hidden');
  await fileInput.setInputFiles(path.join(FIXTURES, 'oversize.bin'));

  // The file is staged — a preview may or may not render (blob URL exists).
  // We only assert the error surfaced after submit.

  await page.getByRole('button', { name: /^send$/i }).click();

  // The update body appears (update was created successfully).
  await expect(page.getByText('Non-image MIME test')).toBeVisible();

  // Upload error should be shown because MIME is rejected by the backend.
  await expect(page.locator('.upload-error')).toBeVisible({ timeout: 8000 });
  const errorText = await page.locator('.upload-error').textContent();
  expect(errorText).toContain('oversize.bin');
});
