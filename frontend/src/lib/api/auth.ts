import { request } from './client';
import type { MemberRole } from '$lib/types/member';

export interface AuthResponse {
	token: string;
	member_id: string;
	role: MemberRole;
	topic_id: string;
}

export function verifyMagicLink(signedToken: string): Promise<AuthResponse> {
	return request('/auth/verify', {
		method: 'POST',
		body: JSON.stringify({ token: signedToken })
	});
}
