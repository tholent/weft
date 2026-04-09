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

import { writable, derived } from 'svelte/store';
import type { MemberRole } from '$lib/types/member';

interface SessionState {
	token: string | null;
	memberId: string | null;
	role: MemberRole | null;
	topicId: string | null;
}

const initial: SessionState = {
	token: typeof localStorage !== 'undefined' ? localStorage.getItem('weft_token') : null,
	memberId: typeof localStorage !== 'undefined' ? localStorage.getItem('weft_member_id') : null,
	role: (typeof localStorage !== 'undefined' ? localStorage.getItem('weft_role') : null) as MemberRole | null,
	topicId: typeof localStorage !== 'undefined' ? localStorage.getItem('weft_topic_id') : null
};

export const session = writable<SessionState>(initial);

export const isAuthenticated = derived(session, ($s) => $s.token !== null);
export const isCreator = derived(session, ($s) => $s.role === 'creator');
export const isAdmin = derived(session, ($s) => $s.role === 'admin' || $s.role === 'creator');
export const isModerator = derived(
	session,
	($s) => $s.role === 'moderator' || $s.role === 'admin' || $s.role === 'creator'
);

export function login(token: string, memberId: string, role: MemberRole, topicId: string) {
	localStorage.setItem('weft_token', token);
	localStorage.setItem('weft_member_id', memberId);
	localStorage.setItem('weft_role', role);
	localStorage.setItem('weft_topic_id', topicId);
	session.set({ token, memberId, role, topicId });
}

export function logout() {
	localStorage.removeItem('weft_token');
	localStorage.removeItem('weft_member_id');
	localStorage.removeItem('weft_role');
	localStorage.removeItem('weft_topic_id');
	session.set({ token: null, memberId: null, role: null, topicId: null });
}
