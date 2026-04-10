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

import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { request, ApiError } from '$lib/api/client';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a minimal Response-shaped object for vi.fn() to resolve. */
function makeResponse(
	status: number,
	ok: boolean,
	jsonFn: () => Promise<unknown>
): Response {
	return { ok, status, json: jsonFn } as unknown as Response;
}

// ---------------------------------------------------------------------------
// Suite
// ---------------------------------------------------------------------------

describe('api/client', () => {
	let originalFetch: typeof fetch;
	let originalLocation: Location;

	beforeEach(() => {
		originalFetch = globalThis.fetch;
		originalLocation = globalThis.location;
		// Stub location with a plain object so href is assignable.
		Object.defineProperty(globalThis, 'location', {
			value: { href: '' },
			writable: true,
			configurable: true
		});
	});

	afterEach(() => {
		globalThis.fetch = originalFetch;
		Object.defineProperty(globalThis, 'location', {
			value: originalLocation,
			writable: true,
			configurable: true
		});
	});

	// 1. Bearer header injected when localStorage has weft_token
	test('injects Authorization header when weft_token is present', async () => {
		localStorage.setItem('weft_token', 'abc');
		const mockFetch = vi.fn().mockResolvedValue(
			makeResponse(200, true, async () => ({}))
		);
		globalThis.fetch = mockFetch;

		await request('/ping');

		const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		const headers = init.headers as Record<string, string>;
		expect(headers['Authorization']).toBe('Bearer abc');
	});

	// 2. No Authorization header when weft_token is absent
	test('omits Authorization header when weft_token is absent', async () => {
		localStorage.removeItem('weft_token');
		const mockFetch = vi.fn().mockResolvedValue(
			makeResponse(200, true, async () => ({}))
		);
		globalThis.fetch = mockFetch;

		await request('/ping');

		const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		const headers = init.headers as Record<string, string>;
		expect(headers).not.toHaveProperty('Authorization');
	});

	// 3. Default Content-Type is application/json
	test('sets Content-Type application/json by default', async () => {
		const mockFetch = vi.fn().mockResolvedValue(
			makeResponse(200, true, async () => ({}))
		);
		globalThis.fetch = mockFetch;

		await request('/ping');

		const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		const headers = init.headers as Record<string, string>;
		expect(headers['Content-Type']).toBe('application/json');
	});

	// 4. Override Content-Type via options.headers
	test('allows caller to override Content-Type', async () => {
		const mockFetch = vi.fn().mockResolvedValue(
			makeResponse(200, true, async () => ({}))
		);
		globalThis.fetch = mockFetch;

		await request('/ping', { headers: { 'Content-Type': 'multipart/form-data' } });

		const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		const headers = init.headers as Record<string, string>;
		expect(headers['Content-Type']).toBe('multipart/form-data');
	});

	// 5. 401 clears token, redirects, and throws ApiError(401)
	test('401 response clears weft_token, redirects to /, and throws ApiError', async () => {
		localStorage.setItem('weft_token', 'secret');
		const mockFetch = vi.fn().mockResolvedValue(
			makeResponse(401, false, async () => ({}))
		);
		globalThis.fetch = mockFetch;

		await expect(request('/protected')).rejects.toSatisfy(
			(err: unknown) => err instanceof ApiError && (err as ApiError).status === 401
		);

		expect(localStorage.getItem('weft_token')).toBeNull();
		expect(globalThis.location.href).toBe('/');
	});

	// 6. Non-2xx with JSON detail field
	test('non-2xx with JSON detail throws ApiError with that message', async () => {
		const mockFetch = vi.fn().mockResolvedValue(
			makeResponse(500, false, async () => ({ detail: 'boom' }))
		);
		globalThis.fetch = mockFetch;

		await expect(request('/fail')).rejects.toSatisfy(
			(err: unknown) =>
				err instanceof ApiError &&
				(err as ApiError).status === 500 &&
				(err as ApiError).message === 'boom'
		);
	});

	// 7. Non-2xx with unparseable body falls back to "Unknown error"
	test('non-2xx with unparseable body throws ApiError with "Unknown error"', async () => {
		const mockFetch = vi.fn().mockResolvedValue(
			makeResponse(500, false, async () => {
				throw new Error('bad json');
			})
		);
		globalThis.fetch = mockFetch;

		await expect(request('/fail')).rejects.toSatisfy(
			(err: unknown) =>
				err instanceof ApiError &&
				(err as ApiError).status === 500 &&
				(err as ApiError).message === 'Unknown error'
		);
	});

	// 8. 204 resolves undefined (early return before json())
	test('204 response resolves to undefined', async () => {
		const mockFetch = vi.fn().mockResolvedValue(
			makeResponse(204, true, async () => ({}))
		);
		globalThis.fetch = mockFetch;

		const result = await request('/x');
		expect(result).toBeUndefined();
	});

	// 9. 200 JSON resolves the parsed body
	test('200 response resolves to parsed JSON body', async () => {
		const mockFetch = vi.fn().mockResolvedValue(
			makeResponse(200, true, async () => ({ foo: 'bar' }))
		);
		globalThis.fetch = mockFetch;

		const result = await request('/data');
		expect(result).toEqual({ foo: 'bar' });
	});

	// 10. URL built from API_BASE + path
	test('builds URL as /api + path', async () => {
		const mockFetch = vi.fn().mockResolvedValue(
			makeResponse(200, true, async () => ({}))
		);
		globalThis.fetch = mockFetch;

		await request('/ping');

		const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
		expect(url).toBe('/api/ping');
	});
});
