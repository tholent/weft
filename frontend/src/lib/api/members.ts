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

import type { Member, MemberRole } from '$lib/types/member';
import { request } from './client';

export function inviteMember(topicId: string, email: string, circle_id: string, role: MemberRole = 'recipient'): Promise<Member> {
	return request(`/topics/${topicId}/members`, {
		method: 'POST',
		body: JSON.stringify({ email, circle_id, role })
	});
}

export async function listMembers(topicId: string): Promise<Member[]> {
	const data = await request<{ items: Member[] }>(`/topics/${topicId}/members`);
	return data.items;
}

export function moveMember(topicId: string, memberId: string, new_circle_id: string, retroactive_revoke = false): Promise<void> {
	return request(`/topics/${topicId}/members/${memberId}/circle`, {
		method: 'PATCH',
		body: JSON.stringify({ new_circle_id, retroactive_revoke })
	});
}

export function promoteMember(topicId: string, memberId: string, new_role: MemberRole): Promise<void> {
	return request(`/topics/${topicId}/members/${memberId}/role`, {
		method: 'PATCH',
		body: JSON.stringify({ new_role })
	});
}

export function renameMember(topicId: string, memberId: string, display_handle: string): Promise<void> {
	return request(`/topics/${topicId}/members/${memberId}/handle`, {
		method: 'PATCH',
		body: JSON.stringify({ display_handle })
	});
}

export function resendInvite(topicId: string, memberId: string): Promise<void> {
	return request(`/topics/${topicId}/members/${memberId}/resend-invite`, { method: 'POST' });
}
