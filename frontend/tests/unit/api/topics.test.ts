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
import { createTopic, getTopic, closeTopic } from '$lib/api/topics';
import { makeTopic } from '../fixtures';
import type { TopicCreateResponse } from '$lib/types/topic';

// ---------------------------------------------------------------------------
// createTopic
// ---------------------------------------------------------------------------

describe('createTopic', () => {
	it('posts to /api/topics with default_title and creator_email', async () => {
		let capturedBody: unknown;
		const fakeTopic = makeTopic({ id: 'topic-1', default_title: 'My Event' });
		const fakeResponse: TopicCreateResponse = {
			topic: fakeTopic,
			token: 'raw-token-xyz',
			magic_link: 'https://example.com/auth?t=signed'
		};

		server.use(
			http.post('http://localhost/api/topics', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(fakeResponse);
			})
		);

		const result = await createTopic('My Event', 'creator@example.com');

		expect(capturedBody).toEqual({
			default_title: 'My Event',
			creator_email: 'creator@example.com'
		});
		expect(result.topic.default_title).toBe('My Event');
		expect(result.token).toBe('raw-token-xyz');
		expect(result.magic_link).toBe('https://example.com/auth?t=signed');
	});

	it('posts to /api/topics with only default_title when creator_email is omitted', async () => {
		let capturedBody: unknown;
		const fakeResponse: TopicCreateResponse = {
			topic: makeTopic({ default_title: 'No Email Topic' }),
			token: 'tok-abc',
			magic_link: 'https://example.com/auth?t=abc'
		};

		server.use(
			http.post('http://localhost/api/topics', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(fakeResponse);
			})
		);

		await createTopic('No Email Topic');

		expect(capturedBody).toEqual({
			default_title: 'No Email Topic',
			creator_email: undefined
		});
	});
});

// ---------------------------------------------------------------------------
// getTopic
// ---------------------------------------------------------------------------

describe('getTopic', () => {
	it('sends GET to /api/topics/:id and returns the topic', async () => {
		let capturedMethod: string | undefined;
		const fakeTopic = makeTopic({ id: 'topic-99', default_title: 'Existing Topic' });

		server.use(
			http.get('http://localhost/api/topics/:id', ({ request }) => {
				capturedMethod = request.method;
				return HttpResponse.json(fakeTopic);
			})
		);

		const result = await getTopic('topic-99');

		expect(capturedMethod).toBe('GET');
		expect(result.id).toBe('topic-99');
		expect(result.default_title).toBe('Existing Topic');
	});

	it('requests the correct topic id in the URL path', async () => {
		let capturedUrl: string | undefined;
		const fakeTopic = makeTopic({ id: 'topic-abc' });

		server.use(
			http.get('http://localhost/api/topics/:id', ({ request }) => {
				capturedUrl = request.url;
				return HttpResponse.json(fakeTopic);
			})
		);

		await getTopic('topic-abc');

		expect(capturedUrl).toContain('/api/topics/topic-abc');
	});
});

// ---------------------------------------------------------------------------
// closeTopic
// ---------------------------------------------------------------------------

describe('closeTopic', () => {
	it('sends POST to /api/topics/:id/close and returns the updated topic', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;
		const fakeTopic = makeTopic({ id: 'topic-55', status: 'closed' });

		server.use(
			http.post('http://localhost/api/topics/:id/close', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return HttpResponse.json(fakeTopic);
			})
		);

		const result = await closeTopic('topic-55');

		expect(capturedMethod).toBe('POST');
		expect(capturedUrl).toContain('/api/topics/topic-55/close');
		expect(result.id).toBe('topic-55');
		expect(result.status).toBe('closed');
	});
});
