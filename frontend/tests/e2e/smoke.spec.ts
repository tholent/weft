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

test('homepage renders', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Weft/i);
});

test('owner magic link redirects to manage', async ({ page, seededTopic }) => {
  await page.goto(`/auth?t=${seededTopic.ownerMagic}`);
  await page.waitForURL(/\/manage\/[^/]+/);
  expect(page.url()).toMatch(/\/manage\/[^/]+/);
});

test('recipient magic link redirects to topic', async ({ page, seededTopic }) => {
  const recipientMagic = Object.values(seededTopic.recipientMagic)[0];

  if (!recipientMagic) {
    // TODO: enable once default spec includes recipients
    test.skip();
    return;
  }

  await page.goto(`/auth?t=${recipientMagic}`);
  await page.waitForURL(/\/topic\/[^/]+/);
  expect(page.url()).toMatch(/\/topic\/[^/]+/);
});
