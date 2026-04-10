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
import { verifyMagicLink } from '$lib/api/auth';
import { makeAuthResponse } from '../fixtures';

// ---------------------------------------------------------------------------
// verifyMagicLink
// ---------------------------------------------------------------------------

describe('verifyMagicLink', () => {
	it('sends POST to /api/auth/verify with the signed token in the body', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;
		let capturedBody: unknown;
		const fakeResponse = makeAuthResponse({
			token: 'session-token-abc',
			member_id: 'member-42',
			role: 'recipient',
			topic_id: 'topic-7'
		});

		server.use(
			http.post('http://localhost/api/auth/verify', async ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				capturedBody = await request.json();
				return HttpResponse.json(fakeResponse);
			})
		);

		const result = await verifyMagicLink('signed-magic-link-token');

		expect(capturedMethod).toBe('POST');
		expect(capturedUrl).toContain('/api/auth/verify');
		expect(capturedBody).toEqual({ token: 'signed-magic-link-token' });
		expect(result.token).toBe('session-token-abc');
		expect(result.member_id).toBe('member-42');
		expect(result.role).toBe('recipient');
		expect(result.topic_id).toBe('topic-7');
	});

	it('returns the full AuthResponse shape including all required fields', async () => {
		const fakeResponse = makeAuthResponse({
			token: 'tok-owner',
			member_id: 'member-1',
			role: 'owner',
			topic_id: 'topic-1'
		});

		server.use(
			http.post('http://localhost/api/auth/verify', async () => {
				return HttpResponse.json(fakeResponse);
			})
		);

		const result = await verifyMagicLink('another-signed-token');

		expect(result).toEqual({
			token: 'tok-owner',
			member_id: 'member-1',
			role: 'owner',
			topic_id: 'topic-1'
		});
	});

	it('sends a different signed token correctly for each call', async () => {
		const bodies: unknown[] = [];

		server.use(
			http.post('http://localhost/api/auth/verify', async ({ request }) => {
				bodies.push(await request.json());
				return HttpResponse.json(makeAuthResponse());
			})
		);

		await verifyMagicLink('token-first');
		await verifyMagicLink('token-second');

		expect(bodies[0]).toEqual({ token: 'token-first' });
		expect(bodies[1]).toEqual({ token: 'token-second' });
	});
});
