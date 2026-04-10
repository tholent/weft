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

import { describe, expect, it, vi } from 'vitest';
import type { Page } from '@sveltejs/kit';
import { mockGoto, mockPageStore } from './sveltekit';

// NOTE: vi.mock calls are hoisted to the top of the module by Vitest, so these
// factory functions run before any imports are evaluated.  The spy and store
// references are captured at module scope so they are available when the
// hoisted factories execute.

const gotoSpy = mockGoto();
const pageStore = mockPageStore({
	url: new URL('http://localhost/topic/abc') as unknown as Page['url']
});

vi.mock('$app/navigation', () => ({ goto: gotoSpy }));
vi.mock('$app/stores', () => ({ page: pageStore }));

// Dynamic imports guarantee we get the mocked module after vi.mock is wired.
const { goto } = await import('$app/navigation');
const { page } = await import('$app/stores');

describe('SvelteKit module mocks', () => {
	describe('mockGoto', () => {
		it('returns a spy that records calls with a path argument', async () => {
			await goto('/x');
			expect(gotoSpy).toHaveBeenCalledWith('/x');
		});

		it('the re-imported goto is the same spy reference', () => {
			expect(goto).toBe(gotoSpy);
		});
	});

	describe('mockPageStore', () => {
		it('yields the overridden URL when subscribed', () => {
			let snapshot: Page | undefined;

			const unsubscribe = page.subscribe((value) => {
				snapshot = value as Page;
			});
			unsubscribe();

			expect(snapshot?.url.href).toBe('http://localhost/topic/abc');
		});

		it('preserves default status of 200', () => {
			let snapshot: Page | undefined;

			const unsubscribe = page.subscribe((value) => {
				snapshot = value as Page;
			});
			unsubscribe();

			expect(snapshot?.status).toBe(200);
		});

		it('preserves default empty params', () => {
			let snapshot: Page | undefined;

			const unsubscribe = page.subscribe((value) => {
				snapshot = value as Page;
			});
			unsubscribe();

			expect(snapshot?.params).toEqual({});
		});
	});
});
