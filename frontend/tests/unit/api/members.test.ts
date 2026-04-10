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
import {
	inviteMember,
	listMembers,
	moveMember,
	promoteMember,
	renameMember,
	resendInvite
} from '$lib/api/members';
import { makeMember } from '../fixtures';

// ---------------------------------------------------------------------------
// inviteMember
// ---------------------------------------------------------------------------

describe('inviteMember', () => {
	it('sends POST to /api/topics/:topicId/members', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.post('http://localhost/api/topics/:topicId/members', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return HttpResponse.json(makeMember());
			})
		);

		await inviteMember('topic-1', 'circle-1');

		expect(capturedMethod).toBe('POST');
		expect(capturedUrl).toContain('/api/topics/topic-1/members');
	});

	it('coerces empty string email to undefined in the request body', async () => {
		let capturedBody: unknown;

		server.use(
			http.post('http://localhost/api/topics/:topicId/members', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(makeMember());
			})
		);

		// Empty string email should be coerced to undefined via `email || undefined`
		await inviteMember('topic-1', 'circle-1', 'recipient', undefined, '');

		// JSON.stringify drops undefined keys — email key should not appear in the body
		expect((capturedBody as Record<string, unknown>).email).toBeUndefined();
	});

	it('coerces empty string phone to undefined in the request body', async () => {
		let capturedBody: unknown;

		server.use(
			http.post('http://localhost/api/topics/:topicId/members', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(makeMember());
			})
		);

		await inviteMember('topic-1', 'circle-1', 'recipient', undefined, undefined, '');

		expect((capturedBody as Record<string, unknown>).phone).toBeUndefined();
	});

	it('coerces empty string display_handle to undefined in the request body', async () => {
		let capturedBody: unknown;

		server.use(
			http.post('http://localhost/api/topics/:topicId/members', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(makeMember());
			})
		);

		await inviteMember('topic-1', 'circle-1', 'recipient', '');

		expect((capturedBody as Record<string, unknown>).display_handle).toBeUndefined();
	});

	it('sends provided email when non-empty', async () => {
		let capturedBody: unknown;

		server.use(
			http.post('http://localhost/api/topics/:topicId/members', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(makeMember());
			})
		);

		await inviteMember('topic-1', 'circle-1', 'recipient', 'Alice', 'alice@example.com');

		expect((capturedBody as Record<string, unknown>).email).toBe('alice@example.com');
		expect((capturedBody as Record<string, unknown>).display_handle).toBe('Alice');
	});

	it('defaults role to recipient when not provided', async () => {
		let capturedBody: unknown;

		server.use(
			http.post('http://localhost/api/topics/:topicId/members', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(makeMember());
			})
		);

		await inviteMember('topic-1', 'circle-1');

		expect((capturedBody as Record<string, unknown>).role).toBe('recipient');
	});

	it('sends notification_channel when specified', async () => {
		let capturedBody: unknown;

		server.use(
			http.post('http://localhost/api/topics/:topicId/members', async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(makeMember());
			})
		);

		await inviteMember('topic-1', 'circle-1', 'recipient', undefined, undefined, undefined, 'sms');

		expect((capturedBody as Record<string, unknown>).notification_channel).toBe('sms');
	});
});

// ---------------------------------------------------------------------------
// listMembers
// ---------------------------------------------------------------------------

describe('listMembers', () => {
	it('unwraps the {items} envelope and returns a plain array', async () => {
		const m1 = makeMember({ id: 'member-1', role: 'admin' });
		const m2 = makeMember({ id: 'member-2', role: 'recipient' });

		server.use(
			http.get('http://localhost/api/topics/:topicId/members', () => {
				return HttpResponse.json({ items: [m1, m2] });
			})
		);

		const result = await listMembers('topic-1');

		expect(Array.isArray(result)).toBe(true);
		expect(result).toHaveLength(2);
		expect(result[0].id).toBe('member-1');
		expect(result[1].id).toBe('member-2');
	});

	it('sends GET to /api/topics/:topicId/members', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.get('http://localhost/api/topics/:topicId/members', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return HttpResponse.json({ items: [] });
			})
		);

		await listMembers('topic-abc');

		expect(capturedMethod).toBe('GET');
		expect(capturedUrl).toContain('/api/topics/topic-abc/members');
	});

	it('returns an empty array when there are no members', async () => {
		server.use(
			http.get('http://localhost/api/topics/:topicId/members', () => {
				return HttpResponse.json({ items: [] });
			})
		);

		const result = await listMembers('topic-1');

		expect(result).toEqual([]);
	});
});

// ---------------------------------------------------------------------------
// moveMember
// ---------------------------------------------------------------------------

describe('moveMember', () => {
	it('sends PATCH to /api/topics/:topicId/members/:memberId/circle', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.patch('http://localhost/api/topics/:topicId/members/:memberId/circle', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return new HttpResponse(null, { status: 204 });
			})
		);

		await moveMember('topic-1', 'member-1', 'circle-2');

		expect(capturedMethod).toBe('PATCH');
		expect(capturedUrl).toContain('/api/topics/topic-1/members/member-1/circle');
	});

	it('sends retroactive_revoke: false by default', async () => {
		let capturedBody: unknown;

		server.use(
			http.patch(
				'http://localhost/api/topics/:topicId/members/:memberId/circle',
				async ({ request }) => {
					capturedBody = await request.json();
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await moveMember('topic-1', 'member-1', 'circle-2');

		expect(capturedBody).toMatchObject({ retroactive_revoke: false });
	});

	it('sends retroactive_revoke: true when specified', async () => {
		let capturedBody: unknown;

		server.use(
			http.patch(
				'http://localhost/api/topics/:topicId/members/:memberId/circle',
				async ({ request }) => {
					capturedBody = await request.json();
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await moveMember('topic-1', 'member-1', 'circle-2', true);

		expect((capturedBody as Record<string, unknown>).retroactive_revoke).toBe(true);
	});

	it('sends new_circle_id in the request body', async () => {
		let capturedBody: unknown;

		server.use(
			http.patch(
				'http://localhost/api/topics/:topicId/members/:memberId/circle',
				async ({ request }) => {
					capturedBody = await request.json();
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await moveMember('topic-1', 'member-1', 'circle-99');

		expect(capturedBody).toEqual({ new_circle_id: 'circle-99', retroactive_revoke: false });
	});
});

// ---------------------------------------------------------------------------
// promoteMember
// ---------------------------------------------------------------------------

describe('promoteMember', () => {
	it('sends PATCH to /api/topics/:topicId/members/:memberId/role', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.patch('http://localhost/api/topics/:topicId/members/:memberId/role', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return new HttpResponse(null, { status: 204 });
			})
		);

		await promoteMember('topic-1', 'member-1', 'admin');

		expect(capturedMethod).toBe('PATCH');
		expect(capturedUrl).toContain('/api/topics/topic-1/members/member-1/role');
	});

	it('sends new_role in the request body', async () => {
		let capturedBody: unknown;

		server.use(
			http.patch(
				'http://localhost/api/topics/:topicId/members/:memberId/role',
				async ({ request }) => {
					capturedBody = await request.json();
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await promoteMember('topic-1', 'member-1', 'moderator');

		expect(capturedBody).toEqual({ new_role: 'moderator' });
	});

	it('sends new_role: admin when promoting to admin', async () => {
		let capturedBody: unknown;

		server.use(
			http.patch(
				'http://localhost/api/topics/:topicId/members/:memberId/role',
				async ({ request }) => {
					capturedBody = await request.json();
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await promoteMember('topic-1', 'member-2', 'admin');

		expect((capturedBody as Record<string, unknown>).new_role).toBe('admin');
	});
});

// ---------------------------------------------------------------------------
// renameMember
// ---------------------------------------------------------------------------

describe('renameMember', () => {
	it('sends PATCH to /api/topics/:topicId/members/:memberId/handle', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.patch(
				'http://localhost/api/topics/:topicId/members/:memberId/handle',
				({ request }) => {
					capturedMethod = request.method;
					capturedUrl = request.url;
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await renameMember('topic-1', 'member-1', 'NewHandle');

		expect(capturedMethod).toBe('PATCH');
		expect(capturedUrl).toContain('/api/topics/topic-1/members/member-1/handle');
	});

	it('sends display_handle in the request body', async () => {
		let capturedBody: unknown;

		server.use(
			http.patch(
				'http://localhost/api/topics/:topicId/members/:memberId/handle',
				async ({ request }) => {
					capturedBody = await request.json();
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await renameMember('topic-1', 'member-1', 'Alice');

		expect(capturedBody).toEqual({ display_handle: 'Alice' });
	});
});

// ---------------------------------------------------------------------------
// resendInvite
// ---------------------------------------------------------------------------

describe('resendInvite', () => {
	it('sends POST to /api/topics/:topicId/members/:memberId/resend-invite', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.post(
				'http://localhost/api/topics/:topicId/members/:memberId/resend-invite',
				({ request }) => {
					capturedMethod = request.method;
					capturedUrl = request.url;
					return new HttpResponse(null, { status: 204 });
				}
			)
		);

		await resendInvite('topic-1', 'member-1');

		expect(capturedMethod).toBe('POST');
		expect(capturedUrl).toContain('/api/topics/topic-1/members/member-1/resend-invite');
	});
});
