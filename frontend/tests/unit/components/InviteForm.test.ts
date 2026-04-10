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

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import { http, HttpResponse } from 'msw';
import InviteForm from '$lib/components/InviteForm.svelte';
import { session } from '$lib/stores/session';
import { server } from '../mocks/msw-server';
import { makeCircle, makeMember } from '../fixtures';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Seed the session store so $session.topicId is set and role is known. */
function seedSession(role: 'recipient' | 'moderator' | 'admin' | 'owner' = 'admin') {
	session.set({
		token: 'tok-test',
		memberId: 'member-test',
		role,
		topicId: 'topic-test'
	});
}

afterEach(() => {
	// Reset store to a clean baseline; setup.ts handles DOM cleanup + MSW reset.
	session.set({ token: null, memberId: null, role: null, topicId: null });
});

// ---------------------------------------------------------------------------
// Role dropdown
// ---------------------------------------------------------------------------

describe('InviteForm — role dropdown options', () => {
	it('always exposes "recipient" and "moderator" options', () => {
		seedSession('admin');
		const circles = [makeCircle({ id: 'c1', name: 'General' })];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		const options = screen.getAllByRole('option') as HTMLOptionElement[];
		const values = options.map((o) => o.value);
		expect(values).toContain('recipient');
		expect(values).toContain('moderator');
	});

	it('does NOT include "admin" or "owner" when session role is "admin"', () => {
		// admin is not owner — the {#if $isOwner} block should be false
		seedSession('admin');
		const circles = [makeCircle({ id: 'c1', name: 'General' })];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		const options = screen.getAllByRole('option') as HTMLOptionElement[];
		const values = options.map((o) => o.value);
		expect(values).not.toContain('admin');
		expect(values).not.toContain('owner');
	});

	it('does NOT include "admin" or "owner" when session role is "moderator"', () => {
		seedSession('moderator');
		const circles = [makeCircle({ id: 'c1', name: 'General' })];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		const options = screen.getAllByRole('option') as HTMLOptionElement[];
		const values = options.map((o) => o.value);
		expect(values).not.toContain('admin');
		expect(values).not.toContain('owner');
	});

	it('exposes "admin" option when session role is "owner"', () => {
		// owner role → $isOwner is true → admin option rendered
		seedSession('owner');
		const circles = [makeCircle({ id: 'c1', name: 'General' })];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		const options = screen.getAllByRole('option') as HTMLOptionElement[];
		const values = options.map((o) => o.value);
		expect(values).toContain('admin');
	});

	it('does NOT include "owner" even when session role is "owner"', () => {
		seedSession('owner');
		const circles = [makeCircle({ id: 'c1', name: 'General' })];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		const options = screen.getAllByRole('option') as HTMLOptionElement[];
		const values = options.map((o) => o.value);
		expect(values).not.toContain('owner');
	});
});

// ---------------------------------------------------------------------------
// Notification channel default
// ---------------------------------------------------------------------------

describe('InviteForm — notification channel default', () => {
	it('defaults the channel select to "email"', () => {
		seedSession('admin');
		const circles = [makeCircle()];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		// The channel select has options "email" and "sms". Check which is selected.
		const channelSelect = document.querySelector('.channel-select') as HTMLSelectElement;
		expect(channelSelect).not.toBeNull();
		expect(channelSelect.value).toBe('email');
	});

	it('shows the email input and not the phone input by default', () => {
		seedSession('admin');
		const circles = [makeCircle()];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		expect(screen.getByPlaceholderText('Email address')).toBeInTheDocument();
		expect(screen.queryByPlaceholderText('Phone number')).toBeNull();
	});

	it('switches to phone input when channel is changed to "sms"', async () => {
		seedSession('admin');
		const circles = [makeCircle()];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		const channelSelect = document.querySelector('.channel-select') as HTMLSelectElement;
		await fireEvent.change(channelSelect, { target: { value: 'sms' } });

		expect(screen.getByPlaceholderText('Phone number')).toBeInTheDocument();
		expect(screen.queryByPlaceholderText('Email address')).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Submit button disabled / enabled (canSubmit logic)
// ---------------------------------------------------------------------------

describe('InviteForm — submit button validation', () => {
	it('starts with the submit button disabled (no circle or email)', () => {
		seedSession('admin');
		const circles = [makeCircle()];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		const btn = screen.getByRole('button', { name: /invite/i }) as HTMLButtonElement;
		expect(btn).toBeDisabled();
	});

	it('button is still disabled after filling email but without selecting a circle', async () => {
		seedSession('admin');
		const circles = [makeCircle({ id: 'c1', name: 'General' })];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		const emailInput = screen.getByPlaceholderText('Email address');
		await fireEvent.input(emailInput, { target: { value: 'alice@example.com' } });

		const btn = screen.getByRole('button', { name: /invite/i }) as HTMLButtonElement;
		expect(btn).toBeDisabled();
	});

	it('button is enabled after providing email AND selecting a circle', async () => {
		seedSession('admin');
		const circles = [makeCircle({ id: 'c1', name: 'General' })];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		// Fill in email
		const emailInput = screen.getByPlaceholderText('Email address');
		await fireEvent.input(emailInput, { target: { value: 'alice@example.com' } });

		// Select a circle (use the select that has the "Circle…" placeholder)
		const circleSelect = screen.getByDisplayValue('Circle…') as HTMLSelectElement;
		await fireEvent.change(circleSelect, { target: { value: 'c1' } });

		const btn = screen.getByRole('button', { name: /invite/i }) as HTMLButtonElement;
		expect(btn).not.toBeDisabled();
	});

	it('button is disabled when channel is "sms" but phone is empty', async () => {
		seedSession('admin');
		const circles = [makeCircle({ id: 'c1', name: 'General' })];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		// Switch to SMS channel
		const channelSelect = document.querySelector('.channel-select') as HTMLSelectElement;
		await fireEvent.change(channelSelect, { target: { value: 'sms' } });

		// Select a circle
		const circleSelect = screen.getByDisplayValue('Circle…') as HTMLSelectElement;
		await fireEvent.change(circleSelect, { target: { value: 'c1' } });

		// Phone is still empty
		const btn = screen.getByRole('button', { name: /invite/i }) as HTMLButtonElement;
		expect(btn).toBeDisabled();
	});

	it('button is enabled when channel is "sms" AND phone is provided AND circle is selected', async () => {
		seedSession('admin');
		const circles = [makeCircle({ id: 'c1', name: 'General' })];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		// Switch to SMS channel
		const channelSelect = document.querySelector('.channel-select') as HTMLSelectElement;
		await fireEvent.change(channelSelect, { target: { value: 'sms' } });

		// Fill phone
		const phoneInput = screen.getByPlaceholderText('Phone number');
		await fireEvent.input(phoneInput, { target: { value: '+15550001234' } });

		// Select a circle
		const circleSelect = screen.getByDisplayValue('Circle…') as HTMLSelectElement;
		await fireEvent.change(circleSelect, { target: { value: 'c1' } });

		const btn = screen.getByRole('button', { name: /invite/i }) as HTMLButtonElement;
		expect(btn).not.toBeDisabled();
	});
});

// ---------------------------------------------------------------------------
// onInvited callback
// ---------------------------------------------------------------------------

describe('InviteForm — onInvited callback', () => {
	it('calls onInvited with the returned member after a successful submit', async () => {
		seedSession('admin');
		const newMember = makeMember({ id: 'member-new', role: 'recipient' });
		const onInvited = vi.fn();

		server.use(
			http.post('http://localhost/api/topics/:topicId/members', () => {
				return HttpResponse.json(newMember);
			})
		);

		const circles = [makeCircle({ id: 'c1', name: 'General' })];
		render(InviteForm, { props: { circles, onInvited } });

		// Fill email
		const emailInput = screen.getByPlaceholderText('Email address');
		await fireEvent.input(emailInput, { target: { value: 'bob@example.com' } });

		// Select circle
		const circleSelect = screen.getByDisplayValue('Circle…') as HTMLSelectElement;
		await fireEvent.change(circleSelect, { target: { value: 'c1' } });

		// Submit
		const btn = screen.getByRole('button', { name: /invite/i });
		await fireEvent.click(btn);

		// Wait a tick for the async handler to complete
		await new Promise((r) => setTimeout(r, 0));

		expect(onInvited).toHaveBeenCalledOnce();
		expect(onInvited).toHaveBeenCalledWith(newMember);
	});

	it('does not call onInvited when the API returns an error', async () => {
		seedSession('admin');
		const onInvited = vi.fn();

		server.use(
			http.post('http://localhost/api/topics/:topicId/members', () => {
				return HttpResponse.json({ detail: 'Member already exists' }, { status: 409 });
			})
		);

		const circles = [makeCircle({ id: 'c1', name: 'General' })];
		render(InviteForm, { props: { circles, onInvited } });

		// Fill in valid data
		const emailInput = screen.getByPlaceholderText('Email address');
		await fireEvent.input(emailInput, { target: { value: 'bob@example.com' } });
		const circleSelect = screen.getByDisplayValue('Circle…') as HTMLSelectElement;
		await fireEvent.change(circleSelect, { target: { value: 'c1' } });

		const btn = screen.getByRole('button', { name: /invite/i });
		await fireEvent.click(btn);

		await new Promise((r) => setTimeout(r, 0));

		expect(onInvited).not.toHaveBeenCalled();
	});

	it('shows a success message after a successful invite', async () => {
		seedSession('admin');
		const newMember = makeMember({ id: 'member-new2' });

		server.use(
			http.post('http://localhost/api/topics/:topicId/members', () => {
				return HttpResponse.json(newMember);
			})
		);

		const circles = [makeCircle({ id: 'c1', name: 'General' })];
		render(InviteForm, { props: { circles, onInvited: vi.fn() } });

		const emailInput = screen.getByPlaceholderText('Email address');
		await fireEvent.input(emailInput, { target: { value: 'carol@example.com' } });
		const circleSelect = screen.getByDisplayValue('Circle…') as HTMLSelectElement;
		await fireEvent.change(circleSelect, { target: { value: 'c1' } });

		await fireEvent.click(screen.getByRole('button', { name: /invite/i }));
		await new Promise((r) => setTimeout(r, 0));

		expect(screen.getByText(/invite sent to carol@example\.com/i)).toBeInTheDocument();
	});
});
