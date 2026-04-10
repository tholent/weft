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
import { listNotificationPreferences, setNotificationPreference } from '$lib/api/notifications';
import { makeNotificationPreference } from '../fixtures';
import type { NotificationPreferenceUpdate } from '$lib/types/notification';

// ---------------------------------------------------------------------------
// listNotificationPreferences
// ---------------------------------------------------------------------------

describe('listNotificationPreferences', () => {
	it('sends GET to /api/topics/:topicId/members/:memberId/notifications and returns an array', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;
		const prefs = [
			makeNotificationPreference({ id: 'pref-1', channel: 'email', trigger: 'new_update' }),
			makeNotificationPreference({ id: 'pref-2', channel: 'sms', trigger: 'new_reply' })
		];

		server.use(
			http.get(
				'http://localhost/api/topics/:topicId/members/:memberId/notifications',
				({ request }) => {
					capturedMethod = request.method;
					capturedUrl = request.url;
					return HttpResponse.json(prefs);
				}
			)
		);

		const result = await listNotificationPreferences('topic-10', 'member-20');

		expect(capturedMethod).toBe('GET');
		expect(capturedUrl).toContain('/api/topics/topic-10/members/member-20/notifications');
		expect(result).toHaveLength(2);
		expect(result[0].id).toBe('pref-1');
		expect(result[1].id).toBe('pref-2');
	});

	it('encodes the correct topic and member ids in the URL path', async () => {
		let capturedUrl: string | undefined;

		server.use(
			http.get(
				'http://localhost/api/topics/:topicId/members/:memberId/notifications',
				({ request }) => {
					capturedUrl = request.url;
					return HttpResponse.json([]);
				}
			)
		);

		await listNotificationPreferences('topic-abc', 'member-xyz');

		expect(capturedUrl).toContain('/api/topics/topic-abc/members/member-xyz/notifications');
	});
});

// ---------------------------------------------------------------------------
// setNotificationPreference
// ---------------------------------------------------------------------------

describe('setNotificationPreference', () => {
	it('sends PUT to /api/topics/:topicId/members/:memberId/notifications with full payload', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;
		let capturedBody: unknown;
		const updatedPref = makeNotificationPreference({
			id: 'pref-5',
			channel: 'sms',
			trigger: 'new_reply',
			delivery_mode: 'digest'
		});

		server.use(
			http.put(
				'http://localhost/api/topics/:topicId/members/:memberId/notifications',
				async ({ request }) => {
					capturedMethod = request.method;
					capturedUrl = request.url;
					capturedBody = await request.json();
					return HttpResponse.json(updatedPref);
				}
			)
		);

		const payload: NotificationPreferenceUpdate = {
			channel: 'sms',
			trigger: 'new_reply',
			delivery_mode: 'digest'
		};

		const result = await setNotificationPreference('topic-10', 'member-20', payload);

		expect(capturedMethod).toBe('PUT');
		expect(capturedUrl).toContain('/api/topics/topic-10/members/member-20/notifications');
		// Full payload — all three required fields must be present
		expect(capturedBody).toEqual({
			channel: 'sms',
			trigger: 'new_reply',
			delivery_mode: 'digest'
		});
		expect(result.id).toBe('pref-5');
		expect(result.delivery_mode).toBe('digest');
	});

	it('passes all three payload fields regardless of which value changed', async () => {
		let capturedBody: unknown;
		const updatedPref = makeNotificationPreference({
			channel: 'email',
			trigger: 'mod_response',
			delivery_mode: 'muted'
		});

		server.use(
			http.put(
				'http://localhost/api/topics/:topicId/members/:memberId/notifications',
				async ({ request }) => {
					capturedBody = await request.json();
					return HttpResponse.json(updatedPref);
				}
			)
		);

		const payload: NotificationPreferenceUpdate = {
			channel: 'email',
			trigger: 'mod_response',
			delivery_mode: 'muted'
		};

		await setNotificationPreference('topic-x', 'member-y', payload);

		expect(capturedBody).toHaveProperty('channel', 'email');
		expect(capturedBody).toHaveProperty('trigger', 'mod_response');
		expect(capturedBody).toHaveProperty('delivery_mode', 'muted');
	});
});
