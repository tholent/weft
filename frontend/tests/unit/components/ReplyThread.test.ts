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

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import ReplyThread from '$lib/components/ReplyThread.svelte';
import { makeReply } from '../fixtures';

// ---------------------------------------------------------------------------
// Moderator vs non-moderator view
// ---------------------------------------------------------------------------

describe('ReplyThread — moderator view', () => {
	it('shows Approve and Dismiss buttons for a pending reply when isModerator is true', () => {
		const reply = makeReply({ id: 'r1', relay_status: 'pending' });
		render(ReplyThread, { props: { replies: [reply], isModerator: true } });

		expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument();
		expect(screen.getByRole('button', { name: 'Dismiss' })).toBeInTheDocument();
	});

	it('shows Undo button for a dismissed reply when isModerator is true', () => {
		const reply = makeReply({ id: 'r2', relay_status: 'dismissed' });
		render(ReplyThread, { props: { replies: [reply], isModerator: true } });

		expect(screen.getByRole('button', { name: 'Undo' })).toBeInTheDocument();
	});

	it('shows a relayed status badge (no action buttons) for a relayed reply when isModerator is true', () => {
		const reply = makeReply({ id: 'r3', relay_status: 'relayed' });
		render(ReplyThread, { props: { replies: [reply], isModerator: true } });

		expect(screen.queryByRole('button', { name: 'Approve' })).toBeNull();
		expect(screen.queryByRole('button', { name: 'Dismiss' })).toBeNull();
		expect(screen.queryByRole('button', { name: 'Undo' })).toBeNull();
		expect(screen.getByText('relayed')).toBeInTheDocument();
	});
});

describe('ReplyThread — non-moderator view', () => {
	it('does NOT show Approve or Dismiss buttons when isModerator is false', () => {
		const reply = makeReply({ id: 'r4', relay_status: 'pending' });
		render(ReplyThread, { props: { replies: [reply], isModerator: false } });

		expect(screen.queryByRole('button', { name: 'Approve' })).toBeNull();
		expect(screen.queryByRole('button', { name: 'Dismiss' })).toBeNull();
	});

	it('does NOT show Undo button for a dismissed reply when isModerator is false', () => {
		const reply = makeReply({ id: 'r5', relay_status: 'dismissed' });
		render(ReplyThread, { props: { replies: [reply], isModerator: false } });

		expect(screen.queryByRole('button', { name: 'Undo' })).toBeNull();
	});

	it('renders reply body text regardless of isModerator', () => {
		const reply = makeReply({
			id: 'r6',
			body: 'A reply from a recipient',
			relay_status: 'pending'
		});
		render(ReplyThread, { props: { replies: [reply], isModerator: false } });

		expect(screen.getByText('A reply from a recipient')).toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// Relay action
// ---------------------------------------------------------------------------

describe('ReplyThread — relay (Approve) action', () => {
	it('calls onRelay with the reply id when Approve is clicked', async () => {
		const onRelay = vi.fn().mockResolvedValue(undefined);
		const reply = makeReply({ id: 'relay-r1', relay_status: 'pending' });

		render(ReplyThread, { props: { replies: [reply], isModerator: true, onRelay } });

		const approveBtn = screen.getByRole('button', { name: 'Approve' });
		await fireEvent.click(approveBtn);

		expect(onRelay).toHaveBeenCalledOnce();
		expect(onRelay).toHaveBeenCalledWith('relay-r1');
	});

	it('calls onRelay with the reply id when Undo is clicked on a dismissed reply', async () => {
		const onRelay = vi.fn().mockResolvedValue(undefined);
		const reply = makeReply({ id: 'relay-r2', relay_status: 'dismissed' });

		render(ReplyThread, { props: { replies: [reply], isModerator: true, onRelay } });

		const undoBtn = screen.getByRole('button', { name: 'Undo' });
		await fireEvent.click(undoBtn);

		expect(onRelay).toHaveBeenCalledOnce();
		expect(onRelay).toHaveBeenCalledWith('relay-r2');
	});

	it('does not call onRelay when onRelay prop is null', async () => {
		const reply = makeReply({ id: 'relay-r3', relay_status: 'pending' });

		// Even when isModerator is true but onRelay is null, the button is shown but
		// clicking it should be a no-op (guard in relay()).
		render(ReplyThread, { props: { replies: [reply], isModerator: true, onRelay: null } });

		const approveBtn = screen.getByRole('button', { name: 'Approve' });
		// Should not throw
		await fireEvent.click(approveBtn);
		// No assertion beyond "didn't throw" — the guard is an internal no-op.
	});
});

// ---------------------------------------------------------------------------
// Dismiss action
// ---------------------------------------------------------------------------

describe('ReplyThread — dismiss action', () => {
	it('calls onDismiss with the reply id when Dismiss is clicked', async () => {
		const onDismiss = vi.fn().mockResolvedValue(undefined);
		const reply = makeReply({ id: 'dismiss-r1', relay_status: 'pending' });

		render(ReplyThread, { props: { replies: [reply], isModerator: true, onDismiss } });

		const dismissBtn = screen.getByRole('button', { name: 'Dismiss' });
		await fireEvent.click(dismissBtn);

		expect(onDismiss).toHaveBeenCalledOnce();
		expect(onDismiss).toHaveBeenCalledWith('dismiss-r1');
	});

	it('does not call onDismiss when onDismiss prop is null', async () => {
		const reply = makeReply({ id: 'dismiss-r2', relay_status: 'pending' });

		render(ReplyThread, { props: { replies: [reply], isModerator: true, onDismiss: null } });

		const dismissBtn = screen.getByRole('button', { name: 'Dismiss' });
		await fireEvent.click(dismissBtn);
		// No error — internal guard is a no-op.
	});
});

// ---------------------------------------------------------------------------
// Mod responses display
// ---------------------------------------------------------------------------

describe('ReplyThread — mod responses', () => {
	it('renders an existing mod response body and scope', () => {
		const reply = makeReply({
			id: 'mr-r1',
			mod_responses: [
				{
					id: 'mr-1',
					body: 'Thanks for the feedback.',
					author_handle: 'mod_alice',
					scope: 'sender_only',
					created_at: '2026-01-02T00:00:00Z'
				}
			]
		});

		render(ReplyThread, { props: { replies: [reply], isModerator: false } });

		expect(screen.getByText('Thanks for the feedback.')).toBeInTheDocument();
		expect(screen.getByText(/sender_only/)).toBeInTheDocument();
	});

	it('renders multiple mod responses in order', () => {
		const reply = makeReply({
			id: 'mr-r2',
			mod_responses: [
				{
					id: 'mr-a',
					body: 'First response',
					author_handle: null,
					scope: 'sender_only',
					created_at: '2026-01-02T00:00:00Z'
				},
				{
					id: 'mr-b',
					body: 'Second response',
					author_handle: 'mod_bob',
					scope: 'all_circles',
					created_at: '2026-01-03T00:00:00Z'
				}
			]
		});

		render(ReplyThread, { props: { replies: [reply], isModerator: true } });

		expect(screen.getByText('First response')).toBeInTheDocument();
		expect(screen.getByText('Second response')).toBeInTheDocument();
	});

	it('renders "Moderator" as author when author_handle is null', () => {
		const reply = makeReply({
			id: 'mr-r3',
			mod_responses: [
				{
					id: 'mr-c',
					body: 'Anonymous mod response',
					author_handle: null,
					scope: 'sender_circle',
					created_at: '2026-01-04T00:00:00Z'
				}
			]
		});

		render(ReplyThread, { props: { replies: [reply], isModerator: false } });

		// The component renders "Moderator" when author_handle is null
		expect(screen.getByText(/Moderator/)).toBeInTheDocument();
	});

	it('does not render mod-responses section when mod_responses is empty', () => {
		const reply = makeReply({ id: 'mr-r4', mod_responses: [] });

		render(ReplyThread, { props: { replies: [reply], isModerator: false } });

		expect(document.querySelector('.mod-responses')).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// wants_to_share badge
// ---------------------------------------------------------------------------

describe('ReplyThread — wants_to_share badge', () => {
	it('renders the Shared badge when wants_to_share is true', () => {
		const reply = makeReply({ id: 'ws-r1', wants_to_share: true });

		render(ReplyThread, { props: { replies: [reply], isModerator: false } });

		expect(screen.getByText('Shared')).toBeInTheDocument();
	});

	it('does not render the Shared badge when wants_to_share is false', () => {
		const reply = makeReply({ id: 'ws-r2', wants_to_share: false });

		render(ReplyThread, { props: { replies: [reply], isModerator: false } });

		expect(screen.queryByText('Shared')).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Anonymous vs named author
// ---------------------------------------------------------------------------

describe('ReplyThread — author display', () => {
	it('shows the author_handle when set', () => {
		const reply = makeReply({ id: 'auth-r1', author_handle: 'alice_wonder' });

		render(ReplyThread, { props: { replies: [reply], isModerator: false } });

		expect(screen.getByText('alice_wonder')).toBeInTheDocument();
	});

	it('shows "Anonymous" when author_handle is null', () => {
		const reply = makeReply({ id: 'auth-r2', author_handle: null });

		render(ReplyThread, { props: { replies: [reply], isModerator: false } });

		expect(screen.getByText('Anonymous')).toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// Empty replies list
// ---------------------------------------------------------------------------

describe('ReplyThread — empty state', () => {
	it('renders the container but no reply elements when replies is empty', () => {
		render(ReplyThread, { props: { replies: [], isModerator: false } });

		expect(document.querySelector('.reply-thread')).toBeInTheDocument();
		expect(document.querySelectorAll('.reply')).toHaveLength(0);
	});
});
