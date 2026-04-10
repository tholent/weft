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

// FT-24: E1 landing flow E2E
// Tests the topic creation form on the landing page (/).
// No seededTopic fixture needed — the landing page creates a topic from scratch.

test('creates topic without email and shows magic link', async ({ page }) => {
  await page.goto('/');

  await page.getByPlaceholder("e.g. Dad's recovery update").fill('E2E test topic');
  await page.getByRole('button', { name: /begin/i }).click();

  // Wait for the success state to appear
  await expect(page.locator('.success')).toBeVisible();
  await expect(page.getByRole('heading', { name: /topic created/i })).toBeVisible();

  // Magic link anchor should be visible when no email is provided
  const magicLink = page.locator('a.magic-link');
  await expect(magicLink).toBeVisible();

  // Optionally verify the magic link href looks like a valid URL
  const href = await magicLink.getAttribute('href');
  expect(href).toBeTruthy();
  expect(href).toMatch(/^https?:\/\//);

  // NOTE: No copy-to-clipboard button exists in the landing page source.
  // The success state renders only the anchor element with class "magic-link".
  // If a copy button is added in the future, add clipboard assertions here.
});

test('creates topic with email and shows check-your-email message', async ({ page }) => {
  await page.goto('/');

  await page.getByPlaceholder("e.g. Dad's recovery update").fill('E2E test topic with email');
  await page.getByPlaceholder('you@example.com').fill('e2e-test@example.com');
  await page.getByRole('button', { name: /begin/i }).click();

  // Wait for the success state to appear
  await expect(page.locator('.success')).toBeVisible();
  await expect(page.getByRole('heading', { name: /topic created/i })).toBeVisible();

  // Email path shows a "Check your email" message
  await expect(page.getByText(/check your email/i)).toBeVisible();

  // Magic link anchor must NOT be visible — the email path deliberately omits it
  await expect(page.locator('a.magic-link')).not.toBeVisible();
});

test('rejects empty title without submitting', async ({ page }) => {
  await page.goto('/');

  // Click submit without filling in the title field
  await page.getByRole('button', { name: /begin/i }).click();

  // The HTML `required` attribute on the title input prevents form submission,
  // so the success view should remain hidden.
  // Assert that the success container is not present / not visible.
  await expect(page.locator('.success')).not.toBeVisible();

  // The title input should be in the :invalid pseudo-state due to the
  // `required` attribute. Playwright evaluates pseudo-class selectors via
  // locator evaluation rather than CSS pseudo-class matching directly, so we
  // check that the success state was never shown as the primary assertion above.
  // The :invalid check below is a secondary confirmation.
  // TODO selector: Playwright does not support :invalid as a CSS selector in
  //   locator() directly; evaluate it via evaluate() instead.
  const titleInput = page.getByPlaceholder("e.g. Dad's recovery update");
  const isInvalid = await titleInput.evaluate((el: HTMLInputElement) => !el.validity.valid);
  expect(isInvalid).toBe(true);
});
