import type { Member, MemberRole } from '$lib/types/member';
import { request } from './client';

export function inviteMember(topicId: string, email: string, circle_id: string, role: MemberRole = 'recipient'): Promise<Member> {
	return request(`/topics/${topicId}/members`, {
		method: 'POST',
		body: JSON.stringify({ email, circle_id, role })
	});
}

export function listMembers(topicId: string): Promise<Member[]> {
	return request(`/topics/${topicId}/members`);
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

export function resendInvite(topicId: string, memberId: string): Promise<void> {
	return request(`/topics/${topicId}/members/${memberId}/resend-invite`, { method: 'POST' });
}
