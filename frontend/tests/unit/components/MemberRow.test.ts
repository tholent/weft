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

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import MemberRow from '$lib/components/MemberRow.svelte';
import { session } from '$lib/stores/session';
import { makeMember, makeCircle } from '../fixtures';

// Seed the session store with a known topicId before every test so that the
// component's internal API calls have a non-null topicId to work with.
beforeEach(() => {
	session.set({ token: 'tok', memberId: 'viewer-1', role: 'owner', topicId: 'topic-1' });
});

// ---------------------------------------------------------------------------
// Promote-to-admin permission guard
// ---------------------------------------------------------------------------
//
// This asserts the client-side enforcement of backend invariant #3:
// only the owner role may promote members to admin. The control must be
// completely absent for non-owner viewers, not just disabled.

describe('MemberRow — promote-to-admin permission guard (invariant #3)', () => {
	it('hides promote-to-admin control when viewer is admin', () => {
		// An admin-role viewer must NOT see the "Make Admin" button at all.
		// The control must be absent from the DOM, not merely disabled.
		const member = makeMember({ id: 'm1', role: 'recipient', display_handle: 'Alice' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'admin' } });

		// queryByRole returns null when the element is not in the DOM.
		const makeAdminBtn = screen.queryByRole('button', { name: /make admin/i });
		expect(makeAdminBtn).toBeNull();
	});

	it('shows promote-to-admin control when viewer is owner', () => {
		// An owner-role viewer MUST see the "Make Admin" button for a recipient member.
		const member = makeMember({ id: 'm1', role: 'recipient', display_handle: 'Alice' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'owner' } });

		const makeAdminBtn = screen.getByRole('button', { name: /make admin/i });
		expect(makeAdminBtn).toBeInTheDocument();
	});

	it('hides promote-to-admin control when viewer is moderator', () => {
		// Moderators have no promotion rights; control must be absent.
		const member = makeMember({ id: 'm1', role: 'recipient', display_handle: 'Alice' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'moderator' } });

		const makeAdminBtn = screen.queryByRole('button', { name: /make admin/i });
		expect(makeAdminBtn).toBeNull();
	});

	it('hides promote-to-admin control when the member is already admin', () => {
		// Even for an owner viewer, the button should not appear when the
		// target member already holds admin role.
		const member = makeMember({ id: 'm1', role: 'admin', display_handle: 'Bob' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'owner' } });

		const makeAdminBtn = screen.queryByRole('button', { name: /make admin/i });
		expect(makeAdminBtn).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Basic member rendering
// ---------------------------------------------------------------------------

describe('MemberRow — basic rendering', () => {
	it('renders the member display handle', () => {
		const member = makeMember({ display_handle: 'Charlie', role: 'recipient' });
		render(MemberRow, { props: { member, circles: [], viewerRole: 'owner' } });

		expect(screen.getByText('Charlie')).toBeInTheDocument();
	});

	it('renders "Anonymous" when display_handle is null', () => {
		const member = makeMember({ display_handle: null, role: 'recipient' });
		render(MemberRow, { props: { member, circles: [], viewerRole: 'owner' } });

		expect(screen.getByText('Anonymous')).toBeInTheDocument();
	});

	it('renders the role badge', () => {
		const member = makeMember({ role: 'moderator', display_handle: 'Dana' });
		render(MemberRow, { props: { member, circles: [], viewerRole: 'owner' } });

		const badge = document.querySelector('.role-badge');
		expect(badge).not.toBeNull();
		expect(badge!.textContent).toBe('moderator');
	});
});

// ---------------------------------------------------------------------------
// canManage gate — action controls only visible to owner/admin
// ---------------------------------------------------------------------------

describe('MemberRow — canManage gate', () => {
	it('shows the move-circle select for an owner viewer', () => {
		const member = makeMember({ role: 'recipient', display_handle: 'Eve' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'owner' } });

		// The select element with "Move to..." placeholder should be present.
		const select = screen.getByRole('combobox');
		expect(select).toBeInTheDocument();
	});

	it('hides the action controls for a recipient viewer', () => {
		const member = makeMember({ role: 'recipient', display_handle: 'Frank' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'recipient' } });

		// Neither the circle select nor any promote buttons should be present.
		expect(screen.queryByRole('combobox')).toBeNull();
		expect(screen.queryByRole('button', { name: /make mod/i })).toBeNull();
	});

	it('shows the action controls for an admin viewer', () => {
		const member = makeMember({ role: 'recipient', display_handle: 'Grace' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'admin' } });

		expect(screen.getByRole('combobox')).toBeInTheDocument();
	});

	it('hides the action controls when the target member is owner', () => {
		// The actions block is gated on member.role !== 'owner'.
		const member = makeMember({ role: 'owner', display_handle: 'Hank' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'owner' } });

		expect(screen.queryByRole('combobox')).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Make Mod button — only for recipient members
// ---------------------------------------------------------------------------

describe('MemberRow — make-mod button', () => {
	it('shows Make Mod button for a recipient member viewed by admin', () => {
		const member = makeMember({ role: 'recipient', display_handle: 'Ivy' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'admin' } });

		expect(screen.getByRole('button', { name: /make mod/i })).toBeInTheDocument();
	});

	it('hides Make Mod button when member is already moderator', () => {
		const member = makeMember({ role: 'moderator', display_handle: 'Jack' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'admin' } });

		expect(screen.queryByRole('button', { name: /make mod/i })).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Retroactive checkbox in the move-member control
// ---------------------------------------------------------------------------

describe('MemberRow — retroactive_revoke checkbox', () => {
	it('renders the Retroactive checkbox when actions are visible', () => {
		const member = makeMember({ role: 'recipient', display_handle: 'Kim' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'admin' } });

		// The checkbox is wrapped in a <label class="retro">
		const checkbox = document.querySelector('label.retro input[type="checkbox"]') as HTMLInputElement;
		expect(checkbox).not.toBeNull();
		expect(checkbox).toBeInTheDocument();
	});

	it('Retroactive checkbox is unchecked by default', () => {
		const member = makeMember({ role: 'recipient', display_handle: 'Leo' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'admin' } });

		const checkbox = document.querySelector('label.retro input[type="checkbox"]') as HTMLInputElement;
		expect(checkbox.checked).toBe(false);
	});

	it('Retroactive checkbox becomes checked after clicking', async () => {
		const member = makeMember({ role: 'recipient', display_handle: 'Mia' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'admin' } });

		const checkbox = document.querySelector('label.retro input[type="checkbox"]') as HTMLInputElement;
		await fireEvent.click(checkbox);

		expect(checkbox.checked).toBe(true);
	});

	it('Retroactive checkbox toggles back to unchecked on second click', async () => {
		const member = makeMember({ role: 'recipient', display_handle: 'Ned' });
		const circles = [makeCircle({ id: 'c1', name: 'General' })];

		render(MemberRow, { props: { member, circles, viewerRole: 'admin' } });

		const checkbox = document.querySelector('label.retro input[type="checkbox"]') as HTMLInputElement;
		await fireEvent.click(checkbox);
		expect(checkbox.checked).toBe(true);

		await fireEvent.click(checkbox);
		expect(checkbox.checked).toBe(false);
	});
});

// ---------------------------------------------------------------------------
// Rename button — owner-only edit handle control
// ---------------------------------------------------------------------------

describe('MemberRow — rename handle (owner only)', () => {
	it('shows the rename button for an owner viewer', () => {
		const member = makeMember({ display_handle: 'Olivia', role: 'recipient' });
		render(MemberRow, { props: { member, circles: [], viewerRole: 'owner' } });

		// The rename button has no accessible name text (it uses a unicode pencil symbol),
		// so we locate it by its CSS class.
		const renameBtn = document.querySelector('.rename-btn');
		expect(renameBtn).not.toBeNull();
	});

	it('hides the rename button for an admin viewer', () => {
		const member = makeMember({ display_handle: 'Pat', role: 'recipient' });
		render(MemberRow, { props: { member, circles: [], viewerRole: 'admin' } });

		expect(document.querySelector('.rename-btn')).toBeNull();
	});
});
