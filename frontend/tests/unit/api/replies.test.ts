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

import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/msw-server';
import { getReplies, createReply, relayReply, dismissReply, createModResponse } from '$lib/api/replies';
import { makeReply } from '../fixtures';
import type { ModResponseScope } from '$lib/types/reply';

// ---------------------------------------------------------------------------
// getReplies
// ---------------------------------------------------------------------------

describe('getReplies', () => {
	it('unwraps the {items} envelope and returns a plain array', async () => {
		const r1 = makeReply({ id: 'reply-1', body: 'First reply' });
		const r2 = makeReply({ id: 'reply-2', body: 'Second reply' });

		server.use(
			http.get('http://localhost/api/topics/:topicId/updates/:updateId/replies', () => {
				return HttpResponse.json({ items: [r1, r2] });
			})
		);

		const result = await getReplies('topic-1', 'update-1');

		expect(Array.isArray(result)).toBe(true);
		expect(result).toHaveLength(2);
		expect(result[0].id).toBe('reply-1');
		expect(result[1].id).toBe('reply-2');
	});

	it('sends GET to /api/topics/:topicId/updates/:updateId/replies', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.get('http://localhost/api/topics/:topicId/updates/:updateId/replies', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return HttpResponse.json({ items: [] });
			})
		);

		await getReplies('topic-abc', 'update-xyz');

		expect(capturedMethod).toBe('GET');
		expect(capturedUrl).toContain('/api/topics/topic-abc/updates/update-xyz/replies');
	});

	it('returns an empty array when there are no replies', async () => {
		server.use(
			http.get('http://localhost/api/topics/:topicId/updates/:updateId/replies', () => {
				return HttpResponse.json({ items: [] });
			})
		);

		const result = await getReplies('topic-1', 'update-1');

		expect(result).toEqual([]);
	});
});

// ---------------------------------------------------------------------------
// createReply
// ---------------------------------------------------------------------------

describe('createReply', () => {
	it('sends POST to /api/topics/:topicId/updates/:updateId/replies', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.post('http://localhost/api/topics/:topicId/updates/:updateId/replies', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return HttpResponse.json(makeReply());
			})
		);

		await createReply('topic-1', 'update-1', 'My reply');

		expect(capturedMethod).toBe('POST');
		expect(capturedUrl).toContain('/api/topics/topic-1/updates/update-1/replies');
	});

	it('defaults wants_to_share to false when not provided', async () => {
		let capturedBody: unknown;

		server.use(
			http.post('http://localhost/api/topics/:topicId/updates/:updateId/replies', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(makeReply());
			})
		);

		await createReply('topic-1', 'update-1', 'My reply');

		expect(capturedBody).toMatchObject({ wants_to_share: false });
	});

	it('sends wants_to_share: true when specified', async () => {
		let capturedBody: unknown;

		server.use(
			http.post('http://localhost/api/topics/:topicId/updates/:updateId/replies', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(makeReply());
			})
		);

		await createReply('topic-1', 'update-1', 'Share me', true);

		expect(capturedBody).toMatchObject({ wants_to_share: true });
	});

	it('returns the created Reply object', async () => {
		const fakeReply = makeReply({ id: 'new-reply', body: 'A fresh reply' });

		server.use(
			http.post('http://localhost/api/topics/:topicId/updates/:updateId/replies', () => {
				return HttpResponse.json(fakeReply);
			})
		);

		const result = await createReply('topic-1', 'update-1', 'A fresh reply');

		expect(result.id).toBe('new-reply');
		expect(result.body).toBe('A fresh reply');
	});
});

// ---------------------------------------------------------------------------
// relayReply
// ---------------------------------------------------------------------------

describe('relayReply', () => {
	it('sends POST to /api/topics/:topicId/updates/:updateId/replies/:replyId/relay', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.post(
				'http://localhost/api/topics/:topicId/updates/:updateId/replies/:replyId/relay',
				({ request }) => {
					capturedMethod = request.method;
					capturedUrl = request.url;
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await relayReply('topic-1', 'update-1', 'reply-1');

		expect(capturedMethod).toBe('POST');
		expect(capturedUrl).toContain('/api/topics/topic-1/updates/update-1/replies/reply-1/relay');
	});

	it('sends circle_ids: null when circle_ids is undefined', async () => {
		let capturedBody: unknown;

		server.use(
			http.post(
				'http://localhost/api/topics/:topicId/updates/:updateId/replies/:replyId/relay',
				async ({ request }) => {
					capturedBody = await request.json();
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await relayReply('topic-1', 'update-1', 'reply-1');

		expect(capturedBody).toEqual({ circle_ids: null });
	});

	it('sends circle_ids: null when circle_ids argument is explicitly undefined', async () => {
		let capturedBody: unknown;

		server.use(
			http.post(
				'http://localhost/api/topics/:topicId/updates/:updateId/replies/:replyId/relay',
				async ({ request }) => {
					capturedBody = await request.json();
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await relayReply('topic-1', 'update-1', 'reply-1', undefined);

		// circle_ids must be null in the body, NOT missing from the payload
		expect((capturedBody as Record<string, unknown>)).toHaveProperty('circle_ids');
		expect((capturedBody as Record<string, unknown>).circle_ids).toBeNull();
	});

	it('sends provided circle_ids array when specified', async () => {
		let capturedBody: unknown;

		server.use(
			http.post(
				'http://localhost/api/topics/:topicId/updates/:updateId/replies/:replyId/relay',
				async ({ request }) => {
					capturedBody = await request.json();
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await relayReply('topic-1', 'update-1', 'reply-1', ['circle-1', 'circle-2']);

		expect(capturedBody).toEqual({ circle_ids: ['circle-1', 'circle-2'] });
	});
});

// ---------------------------------------------------------------------------
// dismissReply
// ---------------------------------------------------------------------------

describe('dismissReply', () => {
	it('sends POST to /api/topics/:topicId/updates/:updateId/replies/:replyId/dismiss', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.post(
				'http://localhost/api/topics/:topicId/updates/:updateId/replies/:replyId/dismiss',
				({ request }) => {
					capturedMethod = request.method;
					capturedUrl = request.url;
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await dismissReply('topic-1', 'update-1', 'reply-1');

		expect(capturedMethod).toBe('POST');
		expect(capturedUrl).toContain('/api/topics/topic-1/updates/update-1/replies/reply-1/dismiss');
	});
});

// ---------------------------------------------------------------------------
// createModResponse
// ---------------------------------------------------------------------------

describe('createModResponse', () => {
	it('sends POST to /api/topics/:topicId/updates/:updateId/replies/:replyId/respond', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;
		const fakeModResponse = {
			id: 'mod-1',
			body: 'Mod response body',
			author_handle: null,
			scope: 'sender_only' as ModResponseScope,
			created_at: '2026-01-01T00:00:00Z'
		};

		server.use(
			http.post(
				'http://localhost/api/topics/:topicId/updates/:updateId/replies/:replyId/respond',
				({ request }) => {
					capturedMethod = request.method;
					capturedUrl = request.url;
					return HttpResponse.json(fakeModResponse);
				}
			)
		);

		await createModResponse('topic-1', 'update-1', 'reply-1', 'Mod response body', 'sender_only');

		expect(capturedMethod).toBe('POST');
		expect(capturedUrl).toContain(
			'/api/topics/topic-1/updates/update-1/replies/reply-1/respond'
		);
	});

	it('serializes the scope enum field as a string: sender_only', async () => {
		let capturedBody: unknown;

		server.use(
			http.post(
				'http://localhost/api/topics/:topicId/updates/:updateId/replies/:replyId/respond',
				async ({ request }) => {
					capturedBody = await request.json();
					return HttpResponse.json({
						id: 'mod-1',
						body: 'text',
						author_handle: null,
						scope: 'sender_only',
						created_at: '2026-01-01T00:00:00Z'
					});
				}
			)
		);

		await createModResponse('topic-1', 'update-1', 'reply-1', 'text', 'sender_only');

		expect((capturedBody as Record<string, unknown>).scope).toBe('sender_only');
	});

	it('serializes the scope enum field as a string: sender_circle', async () => {
		let capturedBody: unknown;

		server.use(
			http.post(
				'http://localhost/api/topics/:topicId/updates/:updateId/replies/:replyId/respond',
				async ({ request }) => {
					capturedBody = await request.json();
					return HttpResponse.json({
						id: 'mod-2',
						body: 'text',
						author_handle: null,
						scope: 'sender_circle',
						created_at: '2026-01-01T00:00:00Z'
					});
				}
			)
		);

		await createModResponse('topic-1', 'update-1', 'reply-1', 'text', 'sender_circle');

		expect((capturedBody as Record<string, unknown>).scope).toBe('sender_circle');
	});

	it('serializes the scope enum field as a string: all_circles', async () => {
		let capturedBody: unknown;

		server.use(
			http.post(
				'http://localhost/api/topics/:topicId/updates/:updateId/replies/:replyId/respond',
				async ({ request }) => {
					capturedBody = await request.json();
					return HttpResponse.json({
						id: 'mod-3',
						body: 'text',
						author_handle: null,
						scope: 'all_circles',
						created_at: '2026-01-01T00:00:00Z'
					});
				}
			)
		);

		await createModResponse('topic-1', 'update-1', 'reply-1', 'text', 'all_circles');

		expect((capturedBody as Record<string, unknown>).scope).toBe('all_circles');
	});

	it('serializes body and scope together', async () => {
		let capturedBody: unknown;

		server.use(
			http.post(
				'http://localhost/api/topics/:topicId/updates/:updateId/replies/:replyId/respond',
				async ({ request }) => {
					capturedBody = await request.json();
					return HttpResponse.json({
						id: 'mod-4',
						body: 'Broadcast reply',
						author_handle: null,
						scope: 'all_circles',
						created_at: '2026-01-01T00:00:00Z'
					});
				}
			)
		);

		await createModResponse('topic-1', 'update-1', 'reply-1', 'Broadcast reply', 'all_circles');

		expect(capturedBody).toEqual({ body: 'Broadcast reply', scope: 'all_circles' });
	});
});
