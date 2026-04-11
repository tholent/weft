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
import { getFeed, createUpdate, editUpdate, deleteUpdate } from '$lib/api/updates';
import { makeUpdate } from '../fixtures';

// ---------------------------------------------------------------------------
// getFeed
// ---------------------------------------------------------------------------

describe('getFeed', () => {
	it('unwraps the {items} envelope and returns a plain array', async () => {
		const u1 = makeUpdate({ id: 'update-1', body: 'First' });
		const u2 = makeUpdate({ id: 'update-2', body: 'Second' });

		server.use(
			http.get('http://localhost/api/topics/:topicId/updates', () => {
				return HttpResponse.json({ items: [u1, u2] });
			})
		);

		const result = await getFeed('topic-1');

		expect(Array.isArray(result)).toBe(true);
		expect(result).toHaveLength(2);
		expect(result[0].id).toBe('update-1');
		expect(result[1].id).toBe('update-2');
	});

	it('sends GET to /api/topics/:topicId/updates', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.get('http://localhost/api/topics/:topicId/updates', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return HttpResponse.json({ items: [] });
			})
		);

		await getFeed('topic-abc');

		expect(capturedMethod).toBe('GET');
		expect(capturedUrl).toContain('/api/topics/topic-abc/updates');
	});

	it('returns an empty array when the feed has no updates', async () => {
		server.use(
			http.get('http://localhost/api/topics/:topicId/updates', () => {
				return HttpResponse.json({ items: [] });
			})
		);

		const result = await getFeed('topic-empty');

		expect(result).toEqual([]);
	});
});

// ---------------------------------------------------------------------------
// createUpdate
// ---------------------------------------------------------------------------

describe('createUpdate', () => {
	it('sends POST to /api/topics/:topicId/updates', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;
		const fakeUpdate = makeUpdate({ id: 'new-update' });

		server.use(
			http.post('http://localhost/api/topics/:topicId/updates', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return HttpResponse.json(fakeUpdate);
			})
		);

		await createUpdate('topic-1', 'Hello world', ['circle-1']);

		expect(capturedMethod).toBe('POST');
		expect(capturedUrl).toContain('/api/topics/topic-1/updates');
	});

	it('defaults circle_bodies to {} when not provided', async () => {
		let capturedBody: unknown;

		server.use(
			http.post('http://localhost/api/topics/:topicId/updates', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(makeUpdate());
			})
		);

		await createUpdate('topic-1', 'Hello', ['circle-1']);

		expect(capturedBody).toMatchObject({ circle_bodies: {} });
	});

	it('serializes all fields including explicit circle_bodies', async () => {
		let capturedBody: unknown;

		server.use(
			http.post('http://localhost/api/topics/:topicId/updates', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(makeUpdate());
			})
		);

		await createUpdate('topic-1', 'Hello', ['circle-1', 'circle-2'], {
			'circle-2': 'Variant body'
		});

		expect(capturedBody).toEqual({
			body: 'Hello',
			circle_ids: ['circle-1', 'circle-2'],
			circle_bodies: { 'circle-2': 'Variant body' }
		});
	});

	it('returns the created Update object', async () => {
		const fakeUpdate = makeUpdate({ id: 'created-update', body: 'New post' });

		server.use(
			http.post('http://localhost/api/topics/:topicId/updates', () => {
				return HttpResponse.json(fakeUpdate);
			})
		);

		const result = await createUpdate('topic-1', 'New post', ['circle-1']);

		expect(result.id).toBe('created-update');
		expect(result.body).toBe('New post');
	});
});

// ---------------------------------------------------------------------------
// editUpdate
// ---------------------------------------------------------------------------

describe('editUpdate', () => {
	it('uses HTTP PATCH', async () => {
		let capturedMethod: string | undefined;

		server.use(
			http.patch('http://localhost/api/topics/:topicId/updates/:updateId', ({ request }) => {
				capturedMethod = request.method;
				return HttpResponse.json(makeUpdate());
			})
		);

		await editUpdate('topic-1', 'update-1', 'Edited body');

		expect(capturedMethod).toBe('PATCH');
	});

	it('sends PATCH to the correct URL', async () => {
		let capturedUrl: string | undefined;

		server.use(
			http.patch('http://localhost/api/topics/:topicId/updates/:updateId', ({ request }) => {
				capturedUrl = request.url;
				return HttpResponse.json(makeUpdate());
			})
		);

		await editUpdate('topic-1', 'update-99', 'Updated');

		expect(capturedUrl).toContain('/api/topics/topic-1/updates/update-99');
	});

	it('defaults circle_bodies to {} when not provided', async () => {
		let capturedBody: unknown;

		server.use(
			http.patch('http://localhost/api/topics/:topicId/updates/:updateId', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(makeUpdate());
			})
		);

		await editUpdate('topic-1', 'update-1', 'Some edit');

		expect(capturedBody).toMatchObject({ circle_bodies: {} });
	});

	it('serializes body and circle_bodies', async () => {
		let capturedBody: unknown;

		server.use(
			http.patch('http://localhost/api/topics/:topicId/updates/:updateId', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(makeUpdate());
			})
		);

		await editUpdate('topic-1', 'update-1', 'New text', { 'circle-2': 'Alt text' });

		expect(capturedBody).toEqual({
			body: 'New text',
			circle_bodies: { 'circle-2': 'Alt text' }
		});
	});
});

// ---------------------------------------------------------------------------
// deleteUpdate
// ---------------------------------------------------------------------------

describe('deleteUpdate', () => {
	it('uses HTTP DELETE', async () => {
		let capturedMethod: string | undefined;

		server.use(
			http.delete('http://localhost/api/topics/:topicId/updates/:updateId', ({ request }) => {
				capturedMethod = request.method;
				return new HttpResponse(null, { status: 204 });
			})
		);

		await deleteUpdate('topic-1', 'update-1');

		expect(capturedMethod).toBe('DELETE');
	});

	it('sends DELETE to the correct URL', async () => {
		let capturedUrl: string | undefined;

		server.use(
			http.delete('http://localhost/api/topics/:topicId/updates/:updateId', ({ request }) => {
				capturedUrl = request.url;
				return new HttpResponse(null, { status: 204 });
			})
		);

		await deleteUpdate('topic-55', 'update-77');

		expect(capturedUrl).toContain('/api/topics/topic-55/updates/update-77');
	});
});
