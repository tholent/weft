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

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { uploadAttachment, listAttachments, getAttachmentUrl } from '$lib/api/attachments';
import { ApiError } from '$lib/api/client';
import { makeAttachment } from '../fixtures';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

describe('api/attachments', () => {
	let originalFetch: typeof fetch;
	let originalLocation: Location;

	beforeEach(() => {
		originalFetch = globalThis.fetch;
		originalLocation = globalThis.location;
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

	// ---------------------------------------------------------------------------
	// uploadAttachment
	// ---------------------------------------------------------------------------

	describe('uploadAttachment', () => {
		it('sends POST to /api/topics/:topicId/updates/:updateId/attachments', async () => {
			const fakeAttachment = makeAttachment({ id: 'att-1', filename: 'a.txt' });
			const mockFetch = vi.fn().mockResolvedValue(
				makeResponse(200, true, async () => fakeAttachment)
			);
			globalThis.fetch = mockFetch;

			const file = new File(['hello'], 'a.txt', { type: 'text/plain' });
			await uploadAttachment('topic-1', 'update-1', file);

			const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
			expect(url).toBe('/api/topics/topic-1/updates/update-1/attachments');
			expect(init.method).toBe('POST');
		});

		it('sends FormData body', async () => {
			const fakeAttachment = makeAttachment();
			const mockFetch = vi.fn().mockResolvedValue(
				makeResponse(200, true, async () => fakeAttachment)
			);
			globalThis.fetch = mockFetch;

			const file = new File(['hello'], 'a.txt', { type: 'text/plain' });
			await uploadAttachment('topic-1', 'update-1', file);

			const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
			expect(init.body).toBeInstanceOf(FormData);
		});

		it('does NOT set Content-Type header (lets browser set multipart/form-data boundary)', async () => {
			// The wrapper only calls getAuthHeaders(), which returns {Authorization: ...}.
			// It must NOT pass Content-Type: application/json, as that would break the
			// multipart boundary that the browser sets automatically when body is FormData.
			const fakeAttachment = makeAttachment();
			const mockFetch = vi.fn().mockResolvedValue(
				makeResponse(200, true, async () => fakeAttachment)
			);
			globalThis.fetch = mockFetch;

			localStorage.setItem('weft_token', 'tok-abc');
			const file = new File(['hello'], 'a.txt', { type: 'text/plain' });
			await uploadAttachment('topic-1', 'update-1', file);

			const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
			const headers = init.headers as Record<string, string>;
			// Authorization is present (from token)
			expect(headers['Authorization']).toBe('Bearer tok-abc');
			// Content-Type must NOT be set by the wrapper
			expect(headers).not.toHaveProperty('Content-Type');
		});

		it('injects Authorization header when token is present', async () => {
			const fakeAttachment = makeAttachment();
			const mockFetch = vi.fn().mockResolvedValue(
				makeResponse(200, true, async () => fakeAttachment)
			);
			globalThis.fetch = mockFetch;

			localStorage.setItem('weft_token', 'bearer-token-xyz');
			const file = new File(['hello'], 'a.txt', { type: 'text/plain' });
			await uploadAttachment('topic-1', 'update-1', file);

			const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
			const headers = init.headers as Record<string, string>;
			expect(headers['Authorization']).toBe('Bearer bearer-token-xyz');
		});

		it('omits Authorization header when no token', async () => {
			const fakeAttachment = makeAttachment();
			const mockFetch = vi.fn().mockResolvedValue(
				makeResponse(200, true, async () => fakeAttachment)
			);
			globalThis.fetch = mockFetch;

			localStorage.removeItem('weft_token');
			const file = new File(['hello'], 'a.txt', { type: 'text/plain' });
			await uploadAttachment('topic-1', 'update-1', file);

			const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
			const headers = init.headers as Record<string, string>;
			expect(headers).not.toHaveProperty('Authorization');
		});

		it('returns parsed Attachment on success', async () => {
			const fakeAttachment = makeAttachment({ id: 'att-42', filename: 'photo.jpg' });
			const mockFetch = vi.fn().mockResolvedValue(
				makeResponse(200, true, async () => fakeAttachment)
			);
			globalThis.fetch = mockFetch;

			const file = new File(['data'], 'photo.jpg');
			const result = await uploadAttachment('topic-1', 'update-1', file);

			expect(result.id).toBe('att-42');
			expect(result.filename).toBe('photo.jpg');
		});

		it('401 response clears token, redirects to /, and throws ApiError(401)', async () => {
			localStorage.setItem('weft_token', 'secret');
			const mockFetch = vi.fn().mockResolvedValue(
				makeResponse(401, false, async () => ({}))
			);
			globalThis.fetch = mockFetch;

			const file = new File(['x'], 'x.txt');
			await expect(uploadAttachment('topic-1', 'update-1', file)).rejects.toSatisfy(
				(err: unknown) => err instanceof ApiError && (err as ApiError).status === 401
			);

			expect(localStorage.getItem('weft_token')).toBeNull();
			expect(globalThis.location.href).toBe('/');
		});

		it('non-2xx throws ApiError with detail message', async () => {
			const mockFetch = vi.fn().mockResolvedValue(
				makeResponse(413, false, async () => ({ detail: 'File too large' }))
			);
			globalThis.fetch = mockFetch;

			const file = new File(['x'], 'x.txt');
			await expect(uploadAttachment('topic-1', 'update-1', file)).rejects.toSatisfy(
				(err: unknown) =>
					err instanceof ApiError &&
					(err as ApiError).status === 413 &&
					(err as ApiError).message === 'File too large'
			);
		});

		it('non-2xx with unparseable body throws ApiError with fallback detail', async () => {
			// Source: `body.detail || 'Upload failed'`. The catch returns
			// `{detail: 'Unknown error'}`, which is truthy, so the message is
			// 'Unknown error', not 'Upload failed'. The 'Upload failed' fallback
			// only fires if `body.detail` is itself falsy (e.g. `{detail: ''}`).
			const mockFetch = vi.fn().mockResolvedValue(
				makeResponse(500, false, async () => {
					throw new Error('bad json');
				})
			);
			globalThis.fetch = mockFetch;

			const file = new File(['x'], 'x.txt');
			await expect(uploadAttachment('topic-1', 'update-1', file)).rejects.toSatisfy(
				(err: unknown) =>
					err instanceof ApiError &&
					(err as ApiError).status === 500 &&
					(err as ApiError).message === 'Unknown error'
			);
		});
	});

	// ---------------------------------------------------------------------------
	// listAttachments
	// ---------------------------------------------------------------------------

	describe('listAttachments', () => {
		it('sends GET to /api/topics/:topicId/updates/:updateId/attachments', async () => {
			const fakeList = [makeAttachment({ id: 'att-1' }), makeAttachment({ id: 'att-2' })];
			const mockFetch = vi.fn().mockResolvedValue(
				makeResponse(200, true, async () => fakeList)
			);
			globalThis.fetch = mockFetch;

			const result = await listAttachments('topic-1', 'update-1');

			const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
			expect(url).toBe('/api/topics/topic-1/updates/update-1/attachments');
			// listAttachments omits an explicit method (defaults to GET)
			expect(init.method).toBeUndefined();
			expect(result).toHaveLength(2);
		});

		it('sets Content-Type application/json', async () => {
			const mockFetch = vi.fn().mockResolvedValue(
				makeResponse(200, true, async () => [])
			);
			globalThis.fetch = mockFetch;

			await listAttachments('topic-1', 'update-1');

			const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
			const headers = init.headers as Record<string, string>;
			expect(headers['Content-Type']).toBe('application/json');
		});

		it('throws ApiError on non-2xx', async () => {
			const mockFetch = vi.fn().mockResolvedValue(
				makeResponse(403, false, async () => ({ detail: 'Forbidden' }))
			);
			globalThis.fetch = mockFetch;

			await expect(listAttachments('topic-1', 'update-1')).rejects.toSatisfy(
				(err: unknown) =>
					err instanceof ApiError &&
					(err as ApiError).status === 403 &&
					(err as ApiError).message === 'Forbidden'
			);
		});
	});

	// ---------------------------------------------------------------------------
	// getAttachmentUrl
	// ---------------------------------------------------------------------------

	describe('getAttachmentUrl', () => {
		it('returns /api/topics/:topicId/attachments/:attachmentId', () => {
			const url = getAttachmentUrl('topic-abc', 'att-xyz');
			expect(url).toBe('/api/topics/topic-abc/attachments/att-xyz');
		});

		it('is a pure function — no fetch calls', () => {
			// Verify it returns immediately without making any network requests
			const mockFetch = vi.fn();
			globalThis.fetch = mockFetch;

			getAttachmentUrl('t1', 'a1');

			expect(mockFetch).not.toHaveBeenCalled();
		});
	});
});
