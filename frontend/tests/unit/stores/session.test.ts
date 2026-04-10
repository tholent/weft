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

// IMPORTANT: session.ts reads localStorage at module load time (the `initial`
// const). Tests that exercise initial state MUST prime localStorage BEFORE
// importing the module. The pattern used here is:
//
//   1. Call `vi.resetModules()` to drop any cached module from the registry.
//   2. Set / clear localStorage as needed.
//   3. Use `await import('$lib/stores/session')` (dynamic) inside the test so
//      the module is evaluated fresh with the desired localStorage contents.
//
// Tests that do NOT test initial-load behaviour can import the module at the
// top of the file in the normal static way, but they MUST call `logout()`
// (or `session.set(...)`) before asserting anything to avoid cross-test
// pollution from a shared singleton.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import type { MemberRole } from '$lib/types/member';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Re-import session module after resetting the module registry. */
async function freshImport() {
	vi.resetModules();
	return import('$lib/stores/session');
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('session store', () => {
	// Clean up localStorage between every test so state never leaks.
	beforeEach(() => {
		localStorage.clear();
	});

	afterEach(() => {
		localStorage.clear();
	});

	// -------------------------------------------------------------------------
	// 1. Initial state from localStorage — empty
	// -------------------------------------------------------------------------
	describe('initial state with empty localStorage', () => {
		it('isAuthenticated is false and all session fields are null', async () => {
			localStorage.clear();
			const { session, isAuthenticated } = await freshImport();

			expect(get(isAuthenticated)).toBe(false);
			const state = get(session);
			expect(state.token).toBeNull();
			expect(state.memberId).toBeNull();
			expect(state.role).toBeNull();
			expect(state.topicId).toBeNull();
		});
	});

	// -------------------------------------------------------------------------
	// 2. Initial state from localStorage — populated
	// -------------------------------------------------------------------------
	describe('initial state with populated localStorage', () => {
		it('session has stored values and isAuthenticated is true', async () => {
			localStorage.setItem('weft_token', 'stored-token');
			localStorage.setItem('weft_member_id', 'stored-member');
			localStorage.setItem('weft_role', 'recipient');
			localStorage.setItem('weft_topic_id', 'stored-topic');

			const { session, isAuthenticated } = await freshImport();

			expect(get(isAuthenticated)).toBe(true);
			const state = get(session);
			expect(state.token).toBe('stored-token');
			expect(state.memberId).toBe('stored-member');
			expect(state.role).toBe('recipient');
			expect(state.topicId).toBe('stored-topic');
		});
	});

	// -------------------------------------------------------------------------
	// 3. login() — persists to localStorage AND updates the store
	// -------------------------------------------------------------------------
	describe('login()', () => {
		it('writes all four keys to localStorage', async () => {
			const { login } = await freshImport();

			login('tok-1', 'mem-1', 'admin' as MemberRole, 'top-1');

			expect(localStorage.getItem('weft_token')).toBe('tok-1');
			expect(localStorage.getItem('weft_member_id')).toBe('mem-1');
			expect(localStorage.getItem('weft_role')).toBe('admin');
			expect(localStorage.getItem('weft_topic_id')).toBe('top-1');
		});

		it('updates the session store', async () => {
			const { session, login } = await freshImport();

			login('tok-2', 'mem-2', 'moderator' as MemberRole, 'top-2');

			const state = get(session);
			expect(state.token).toBe('tok-2');
			expect(state.memberId).toBe('mem-2');
			expect(state.role).toBe('moderator');
			expect(state.topicId).toBe('top-2');
		});
	});

	// -------------------------------------------------------------------------
	// 4. logout() — removes all four keys AND nulls the store
	// -------------------------------------------------------------------------
	describe('logout()', () => {
		it('removes all four localStorage keys', async () => {
			const { login, logout } = await freshImport();

			login('t', 'm', 'recipient' as MemberRole, 'tp');
			logout();

			expect(localStorage.getItem('weft_token')).toBeNull();
			expect(localStorage.getItem('weft_member_id')).toBeNull();
			expect(localStorage.getItem('weft_role')).toBeNull();
			expect(localStorage.getItem('weft_topic_id')).toBeNull();
		});

		it('nulls all session store fields', async () => {
			const { session, login, logout } = await freshImport();

			login('t', 'm', 'recipient' as MemberRole, 'tp');
			logout();

			const state = get(session);
			expect(state.token).toBeNull();
			expect(state.memberId).toBeNull();
			expect(state.role).toBeNull();
			expect(state.topicId).toBeNull();
		});
	});

	// -------------------------------------------------------------------------
	// 5. Derived flag: isAuthenticated
	// -------------------------------------------------------------------------
	describe('isAuthenticated derived store', () => {
		it('is true when token is present', async () => {
			const { login, isAuthenticated } = await freshImport();

			login('some-token', 'mem', 'recipient' as MemberRole, 'top');
			expect(get(isAuthenticated)).toBe(true);
		});

		it('is false when token is null (after logout)', async () => {
			const { login, logout, isAuthenticated } = await freshImport();

			login('some-token', 'mem', 'recipient' as MemberRole, 'top');
			logout();
			expect(get(isAuthenticated)).toBe(false);
		});
	});

	// -------------------------------------------------------------------------
	// 6. Derived flag: isOwner
	// -------------------------------------------------------------------------
	describe('isOwner derived store', () => {
		it('is true for role=owner', async () => {
			const { login, isOwner } = await freshImport();
			login('t', 'm', 'owner' as MemberRole, 'tp');
			expect(get(isOwner)).toBe(true);
		});

		it('is true for legacy role=creator', async () => {
			const { session, isOwner } = await freshImport();
			// Cast through unknown since 'creator' is not in the current MemberRole union
			session.set({ token: 't', memberId: 'm', role: 'creator' as unknown as MemberRole, topicId: 'tp' });
			expect(get(isOwner)).toBe(true);
		});

		it('is false for role=admin', async () => {
			const { login, isOwner } = await freshImport();
			login('t', 'm', 'admin' as MemberRole, 'tp');
			expect(get(isOwner)).toBe(false);
		});

		it('is false for role=moderator', async () => {
			const { login, isOwner } = await freshImport();
			login('t', 'm', 'moderator' as MemberRole, 'tp');
			expect(get(isOwner)).toBe(false);
		});

		it('is false for role=recipient', async () => {
			const { login, isOwner } = await freshImport();
			login('t', 'm', 'recipient' as MemberRole, 'tp');
			expect(get(isOwner)).toBe(false);
		});

		it('is false when role is null', async () => {
			const { isOwner } = await freshImport();
			// freshImport with empty localStorage → role is null
			expect(get(isOwner)).toBe(false);
		});
	});

	// -------------------------------------------------------------------------
	// 7. Derived flag: isAdmin
	// -------------------------------------------------------------------------
	describe('isAdmin derived store', () => {
		it('is true for role=admin', async () => {
			const { login, isAdmin } = await freshImport();
			login('t', 'm', 'admin' as MemberRole, 'tp');
			expect(get(isAdmin)).toBe(true);
		});

		it('is true for role=owner', async () => {
			const { login, isAdmin } = await freshImport();
			login('t', 'm', 'owner' as MemberRole, 'tp');
			expect(get(isAdmin)).toBe(true);
		});

		it('is true for legacy role=creator', async () => {
			const { session, isAdmin } = await freshImport();
			session.set({ token: 't', memberId: 'm', role: 'creator' as unknown as MemberRole, topicId: 'tp' });
			expect(get(isAdmin)).toBe(true);
		});

		it('is false for role=moderator', async () => {
			const { login, isAdmin } = await freshImport();
			login('t', 'm', 'moderator' as MemberRole, 'tp');
			expect(get(isAdmin)).toBe(false);
		});

		it('is false for role=recipient', async () => {
			const { login, isAdmin } = await freshImport();
			login('t', 'm', 'recipient' as MemberRole, 'tp');
			expect(get(isAdmin)).toBe(false);
		});

		it('is false when role is null', async () => {
			const { isAdmin } = await freshImport();
			expect(get(isAdmin)).toBe(false);
		});
	});

	// -------------------------------------------------------------------------
	// 8. Derived flag: isModerator
	// -------------------------------------------------------------------------
	describe('isModerator derived store', () => {
		it('is true for role=moderator', async () => {
			const { login, isModerator } = await freshImport();
			login('t', 'm', 'moderator' as MemberRole, 'tp');
			expect(get(isModerator)).toBe(true);
		});

		it('is true for role=admin', async () => {
			const { login, isModerator } = await freshImport();
			login('t', 'm', 'admin' as MemberRole, 'tp');
			expect(get(isModerator)).toBe(true);
		});

		it('is true for role=owner', async () => {
			const { login, isModerator } = await freshImport();
			login('t', 'm', 'owner' as MemberRole, 'tp');
			expect(get(isModerator)).toBe(true);
		});

		it('is true for legacy role=creator', async () => {
			const { session, isModerator } = await freshImport();
			session.set({ token: 't', memberId: 'm', role: 'creator' as unknown as MemberRole, topicId: 'tp' });
			expect(get(isModerator)).toBe(true);
		});

		it('is false for role=recipient', async () => {
			const { login, isModerator } = await freshImport();
			login('t', 'm', 'recipient' as MemberRole, 'tp');
			expect(get(isModerator)).toBe(false);
		});

		it('is false when role is null', async () => {
			const { isModerator } = await freshImport();
			expect(get(isModerator)).toBe(false);
		});
	});

	// -------------------------------------------------------------------------
	// 9. Role transitions — derived flags reflect the latest login
	// -------------------------------------------------------------------------
	describe('role transitions', () => {
		it('reflects updated derived flags after two login calls', async () => {
			const { login, isOwner, isAdmin, isModerator } = await freshImport();

			// First login as owner
			login('tok-a', 'mem-a', 'owner' as MemberRole, 'top-a');
			expect(get(isOwner)).toBe(true);
			expect(get(isAdmin)).toBe(true);
			expect(get(isModerator)).toBe(true);

			// Second login as recipient — flags must flip
			login('tok-b', 'mem-b', 'recipient' as MemberRole, 'top-b');
			expect(get(isOwner)).toBe(false);
			expect(get(isAdmin)).toBe(false);
			expect(get(isModerator)).toBe(false);
		});
	});
});
