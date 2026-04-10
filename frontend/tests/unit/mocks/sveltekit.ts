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
 * SvelteKit module mocks for Vitest unit tests.
 *
 * IMPORTANT: `vi.mock(...)` calls must appear at the TOP of each test file that
 * imports routes or components which use `$app/stores` or `$app/navigation`.
 * Vitest hoists `vi.mock` calls before any imports, so the mock factory runs
 * before the module under test is evaluated.
 *
 * Minimal usage example:
 *
 * ```ts
 * import { vi } from 'vitest';
 * import { mockPageStore, mockGoto } from '../mocks/sveltekit';
 *
 * const gotoSpy = mockGoto();
 * vi.mock('$app/navigation', () => ({ goto: gotoSpy }));
 *
 * vi.mock('$app/stores', () => ({
 *   page: mockPageStore({ url: new URL('http://localhost/topic/abc') })
 * }));
 * ```
 *
 * Each test file that needs different page values should call `mockPageStore`
 * with its own override and install a fresh `vi.mock` factory.
 */

import { writable } from 'svelte/store';
import type { Readable } from 'svelte/store';
import type { Page } from '@sveltejs/kit';
import type { Mock } from 'vitest';
import { vi } from 'vitest';

/**
 * Sensible defaults for a test `Page` object.  The `url` field is typed as
 * `URL & { pathname: ResolvedPathname }` in the kit types, but a plain `URL`
 * satisfies the structural constraint at runtime. We cast via `unknown` so
 * TypeScript's strict mode is happy.
 */
const defaultPage: Page = {
	url: new URL('http://localhost/') as unknown as Page['url'],
	params: {},
	route: { id: null },
	status: 200,
	error: null,
	data: {},
	form: null,
	state: {}
};

/**
 * Returns a writable store (which is also a `Readable<Page>`) pre-seeded with
 * the default page values merged with the provided partial override.
 *
 * Pass this store directly into a `vi.mock('$app/stores', ...)` factory:
 *
 * ```ts
 * vi.mock('$app/stores', () => ({
 *   page: mockPageStore({ url: new URL('http://localhost/topic/abc') })
 * }));
 * ```
 */
export function mockPageStore(partial: Partial<Page> = {}): Readable<Page> {
	return writable<Page>({ ...defaultPage, ...partial });
}

/**
 * Returns a `vi.fn()` spy to be installed as the `goto` export from
 * `$app/navigation`.  Capture the return value before calling `vi.mock`:
 *
 * ```ts
 * const gotoSpy = mockGoto();
 * vi.mock('$app/navigation', () => ({ goto: gotoSpy }));
 * ```
 *
 * Because `vi.mock` factories are hoisted, the spy reference must be captured
 * in the module scope (not inside a `beforeEach`) to be available when the
 * factory executes.
 */
export function mockGoto(): Mock {
	return vi.fn();
}
