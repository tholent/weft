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

import { describe, expect, it } from 'vitest';
import {
	makeAttachment,
	makeAuthResponse,
	makeCircle,
	makeMember,
	makeNotificationPreference,
	makeReply,
	makeTopic,
	makeUpdate
} from './index';

describe('fixture factories smoke tests', () => {
	it('makeTopic returns a fully-populated Topic', () => {
		const topic = makeTopic();
		expect(topic.id).toBeDefined();
		expect(topic.default_title).toBeDefined();
		expect(topic.status).toBeDefined();
		expect(topic.created_at).toBeDefined();
		expect(topic.closed_at).toBeNull();
		expect(topic.scoped_title).toBeNull();
	});

	it('makeTopic accepts deep-partial overrides', () => {
		const topic = makeTopic({ id: 'custom-id', status: 'closed' });
		expect(topic.id).toBe('custom-id');
		expect(topic.status).toBe('closed');
		expect(topic.default_title).toBe('Test Topic');
	});

	it('makeCircle returns a fully-populated Circle', () => {
		const circle = makeCircle();
		expect(circle.id).toBeDefined();
		expect(circle.name).toBeDefined();
		expect(circle.created_at).toBeDefined();
		expect(circle.scoped_title).toBeNull();
	});

	it('makeCircle accepts overrides', () => {
		const circle = makeCircle({ name: 'VIP Circle' });
		expect(circle.name).toBe('VIP Circle');
		expect(circle.id).toBe('circle-1');
	});

	it('makeMember returns a fully-populated Member', () => {
		const member = makeMember();
		expect(member.id).toBeDefined();
		expect(member.role).toBeDefined();
		expect(member.joined_at).toBeDefined();
		expect(member.notification_channel).toBeDefined();
		expect(typeof member.has_email).toBe('boolean');
		expect(typeof member.has_phone).toBe('boolean');
	});

	it('makeMember defaults to recipient role', () => {
		const member = makeMember();
		expect(member.role).toBe('recipient');
	});

	it('makeMember accepts role override', () => {
		const admin = makeMember({ role: 'admin' });
		expect(admin.role).toBe('admin');
	});

	it('makeUpdate returns a fully-populated Update', () => {
		const update = makeUpdate();
		expect(update.id).toBeDefined();
		expect(update.body).toBeDefined();
		expect(update.author_member_id).toBeDefined();
		expect(Array.isArray(update.circle_ids)).toBe(true);
		expect(typeof update.body_variants).toBe('object');
		expect(update.created_at).toBeDefined();
		expect(typeof update.reply_count).toBe('number');
		expect(typeof update.pending_reply_count).toBe('number');
		expect(Array.isArray(update.attachments)).toBe(true);
	});

	it('makeReply returns a fully-populated Reply', () => {
		const reply = makeReply();
		expect(reply.id).toBeDefined();
		expect(reply.body).toBeDefined();
		expect(reply.author_member_id).toBeDefined();
		expect(reply.relay_status).toBeDefined();
		expect(reply.created_at).toBeDefined();
		expect(Array.isArray(reply.mod_responses)).toBe(true);
		expect(typeof reply.wants_to_share).toBe('boolean');
	});

	it('makeReply defaults relay_status to pending', () => {
		const reply = makeReply();
		expect(reply.relay_status).toBe('pending');
	});

	it('makeAttachment returns a fully-populated Attachment', () => {
		const attachment = makeAttachment();
		expect(attachment.id).toBeDefined();
		expect(attachment.update_id).toBeDefined();
		expect(attachment.topic_id).toBeDefined();
		expect(attachment.filename).toBeDefined();
		expect(attachment.content_type).toBeDefined();
		expect(typeof attachment.size_bytes).toBe('number');
		expect(attachment.created_at).toBeDefined();
	});

	it('makeNotificationPreference returns a fully-populated NotificationPreference', () => {
		const pref = makeNotificationPreference();
		expect(pref.id).toBeDefined();
		expect(pref.member_id).toBeDefined();
		expect(pref.channel).toBeDefined();
		expect(pref.trigger).toBeDefined();
		expect(pref.delivery_mode).toBeDefined();
	});

	it('makeNotificationPreference accepts overrides', () => {
		const pref = makeNotificationPreference({ channel: 'sms', delivery_mode: 'digest' });
		expect(pref.channel).toBe('sms');
		expect(pref.delivery_mode).toBe('digest');
	});

	it('makeAuthResponse returns a fully-populated AuthResponse', () => {
		const auth = makeAuthResponse();
		expect(auth.token).toBeDefined();
		expect(auth.member_id).toBeDefined();
		expect(auth.role).toBeDefined();
		expect(auth.topic_id).toBeDefined();
	});

	it('makeAuthResponse accepts role override', () => {
		const auth = makeAuthResponse({ role: 'owner' });
		expect(auth.role).toBe('owner');
		expect(auth.token).toBe('test-token-abc123');
	});
});
