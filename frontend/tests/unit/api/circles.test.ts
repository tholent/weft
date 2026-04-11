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
import { listCircles, createCircle, renameCircle, deleteCircle } from '$lib/api/circles';
import { makeCircle } from '../fixtures';

// ---------------------------------------------------------------------------
// listCircles
// ---------------------------------------------------------------------------

describe('listCircles', () => {
	it('sends GET to /api/topics/:id/circles and returns the array', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;
		const fakeCircles = [
			makeCircle({ id: 'circle-1', name: 'Alpha' }),
			makeCircle({ id: 'circle-2', name: 'Beta' })
		];

		server.use(
			http.get('http://localhost/api/topics/:topicId/circles', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return HttpResponse.json(fakeCircles);
			})
		);

		const result = await listCircles('topic-1');

		expect(capturedMethod).toBe('GET');
		expect(capturedUrl).toContain('/api/topics/topic-1/circles');
		expect(result).toHaveLength(2);
		expect(result[0].name).toBe('Alpha');
		expect(result[1].name).toBe('Beta');
	});

	it('returns an empty array when no circles exist', async () => {
		server.use(
			http.get('http://localhost/api/topics/:topicId/circles', () => {
				return HttpResponse.json([]);
			})
		);

		const result = await listCircles('topic-empty');

		expect(result).toEqual([]);
	});
});

// ---------------------------------------------------------------------------
// createCircle
// ---------------------------------------------------------------------------

describe('createCircle', () => {
	it('sends POST to /api/topics/:id/circles with name and scoped_title', async () => {
		let capturedMethod: string | undefined;
		let capturedBody: unknown;
		const fakeCircle = makeCircle({ id: 'circle-new', name: 'VIP', scoped_title: 'VIP Guests' });

		server.use(
			http.post('http://localhost/api/topics/:topicId/circles', async ({ request }) => {
				capturedMethod = request.method;
				capturedBody = await request.json();
				return HttpResponse.json(fakeCircle);
			})
		);

		const result = await createCircle('topic-1', 'VIP', 'VIP Guests');

		expect(capturedMethod).toBe('POST');
		expect(capturedBody).toEqual({ name: 'VIP', scoped_title: 'VIP Guests' });
		expect(result.id).toBe('circle-new');
		expect(result.name).toBe('VIP');
		expect(result.scoped_title).toBe('VIP Guests');
	});

	it('sends POST with only name when scoped_title is omitted', async () => {
		let capturedBody: unknown;
		const fakeCircle = makeCircle({ name: 'General', scoped_title: null });

		server.use(
			http.post('http://localhost/api/topics/:topicId/circles', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(fakeCircle);
			})
		);

		await createCircle('topic-1', 'General');

		expect(capturedBody).toEqual({ name: 'General', scoped_title: undefined });
	});
});

// ---------------------------------------------------------------------------
// renameCircle
// ---------------------------------------------------------------------------

describe('renameCircle', () => {
	it('sends PATCH to /api/topics/:topicId/circles/:circleId with updated name', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;
		let capturedBody: unknown;
		const fakeCircle = makeCircle({ id: 'circle-7', name: 'Renamed', scoped_title: null });

		server.use(
			http.patch('http://localhost/api/topics/:topicId/circles/:circleId', async ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				capturedBody = await request.json();
				return HttpResponse.json(fakeCircle);
			})
		);

		const result = await renameCircle('topic-1', 'circle-7', 'Renamed');

		expect(capturedMethod).toBe('PATCH');
		expect(capturedUrl).toContain('/api/topics/topic-1/circles/circle-7');
		expect(capturedBody).toEqual({ name: 'Renamed', scoped_title: undefined });
		expect(result.name).toBe('Renamed');
	});

	it('sends PATCH with both name and scoped_title when both are provided', async () => {
		let capturedBody: unknown;
		const fakeCircle = makeCircle({
			id: 'circle-8',
			name: 'Inner Circle',
			scoped_title: 'IC Updates'
		});

		server.use(
			http.patch('http://localhost/api/topics/:topicId/circles/:circleId', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(fakeCircle);
			})
		);

		const result = await renameCircle('topic-1', 'circle-8', 'Inner Circle', 'IC Updates');

		expect(capturedBody).toEqual({ name: 'Inner Circle', scoped_title: 'IC Updates' });
		expect(result.scoped_title).toBe('IC Updates');
	});
});

// ---------------------------------------------------------------------------
// deleteCircle
// ---------------------------------------------------------------------------

describe('deleteCircle', () => {
	it('sends DELETE to /api/topics/:topicId/circles/:circleId', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.delete('http://localhost/api/topics/:topicId/circles/:circleId', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return new HttpResponse(null, { status: 204 });
			})
		);

		const result = await deleteCircle('topic-1', 'circle-9');

		expect(capturedMethod).toBe('DELETE');
		expect(capturedUrl).toContain('/api/topics/topic-1/circles/circle-9');
		expect(result).toBeUndefined();
	});
});
