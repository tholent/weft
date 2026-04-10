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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import PassTheTorch from '$lib/components/PassTheTorch.svelte';
import { session } from '$lib/stores/session';
import { makeMember } from '../fixtures';

vi.mock('$lib/api/transfer', () => ({
	getTransferStatus: vi.fn(),
	requestTransfer: vi.fn(),
	cancelTransfer: vi.fn(),
	directTransfer: vi.fn()
}));

import { directTransfer } from '$lib/api/transfer';

// The owner's member id — used to seed the session so the owner is filtered
// out of the candidates list (PassTheTorch excludes the viewer themselves).
const OWNER_ID = 'owner-member-1';

// Two admin candidates the owner can transfer ownership to
const adminA = makeMember({ id: 'admin-a', role: 'admin', display_handle: 'Alice' });
const adminB = makeMember({ id: 'admin-b', role: 'admin', display_handle: 'Bob' });

beforeEach(() => {
	session.set({ token: 'tok', memberId: OWNER_ID, role: 'owner', topicId: 'topic-1' });
	vi.mocked(directTransfer).mockReset();
});

// ---------------------------------------------------------------------------
// Admin list rendered
// ---------------------------------------------------------------------------
// Note: PassTheTorch accepts `members` (all members) and `onTransferred`
// props. It filters out the current viewer (owner) from the candidates list.

describe('PassTheTorch — admin list', () => {
	it('renders a select with all non-owner member candidates', () => {
		render(PassTheTorch, {
			props: { members: [adminA, adminB], onTransferred: vi.fn() }
		});

		// The select should include both admins
		expect(screen.getByRole('option', { name: /Alice/i })).toBeInTheDocument();
		expect(screen.getByRole('option', { name: /Bob/i })).toBeInTheDocument();
	});

	it('does not include the current owner (viewer) in the candidate list', () => {
		const ownerMember = makeMember({ id: OWNER_ID, role: 'owner', display_handle: 'Owner' });

		render(PassTheTorch, {
			props: { members: [ownerMember, adminA], onTransferred: vi.fn() }
		});

		// The owner should NOT appear as a selectable option
		const options = screen.getAllByRole('option');
		const optionTexts = options.map((o) => o.textContent ?? '');
		expect(optionTexts.some((t) => t.includes('Owner'))).toBe(false);
	});

	it('renders the "Pass the Torch" button in the initial state', () => {
		render(PassTheTorch, {
			props: { members: [adminA], onTransferred: vi.fn() }
		});

		expect(screen.getByRole('button', { name: /pass the torch/i })).toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// "Pass the Torch" button disabled until a selection is made
// ---------------------------------------------------------------------------

describe('PassTheTorch — button disabled until selection', () => {
	it('disables the "Pass the Torch" button when no candidate is selected', () => {
		render(PassTheTorch, {
			props: { members: [adminA, adminB], onTransferred: vi.fn() }
		});

		const btn = screen.getByRole('button', { name: /pass the torch/i });
		expect(btn).toBeDisabled();
	});

	it('enables the "Pass the Torch" button once a candidate is selected', async () => {
		render(PassTheTorch, {
			props: { members: [adminA, adminB], onTransferred: vi.fn() }
		});

		const select = screen.getByRole('combobox');
		await fireEvent.change(select, { target: { value: adminA.id } });

		const btn = screen.getByRole('button', { name: /pass the torch/i });
		expect(btn).not.toBeDisabled();
	});
});

// ---------------------------------------------------------------------------
// Confirmation gate — clicking "Pass the Torch" opens a confirmation step
// ---------------------------------------------------------------------------

describe('PassTheTorch — confirmation gate', () => {
	it('shows a confirmation message after clicking "Pass the Torch"', async () => {
		render(PassTheTorch, {
			props: { members: [adminA], onTransferred: vi.fn() }
		});

		const select = screen.getByRole('combobox');
		await fireEvent.change(select, { target: { value: adminA.id } });

		await fireEvent.click(screen.getByRole('button', { name: /pass the torch/i }));

		// Confirmation message should mention the selected member's name.
		// Use a more specific match because /transfer ownership/i also appears
		// in the section heading.
		expect(screen.getByText(/you are about to transfer ownership/i)).toBeInTheDocument();
		expect(screen.getByText(/Alice/)).toBeInTheDocument();
	});

	it('does NOT call directTransfer after clicking "Pass the Torch" (before confirmation)', async () => {
		render(PassTheTorch, {
			props: { members: [adminA], onTransferred: vi.fn() }
		});

		const select = screen.getByRole('combobox');
		await fireEvent.change(select, { target: { value: adminA.id } });

		await fireEvent.click(screen.getByRole('button', { name: /pass the torch/i }));

		// API must NOT have been called yet
		expect(directTransfer).not.toHaveBeenCalled();
	});

	it('shows "Yes, transfer ownership" and "Cancel" buttons in the confirmation step', async () => {
		render(PassTheTorch, {
			props: { members: [adminA], onTransferred: vi.fn() }
		});

		const select = screen.getByRole('combobox');
		await fireEvent.change(select, { target: { value: adminA.id } });
		await fireEvent.click(screen.getByRole('button', { name: /pass the torch/i }));

		expect(screen.getByRole('button', { name: /yes, transfer ownership/i })).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
	});

	it('returns to the selection view when "Cancel" is clicked in the confirmation step', async () => {
		render(PassTheTorch, {
			props: { members: [adminA], onTransferred: vi.fn() }
		});

		const select = screen.getByRole('combobox');
		await fireEvent.change(select, { target: { value: adminA.id } });
		await fireEvent.click(screen.getByRole('button', { name: /pass the torch/i }));

		// Now in confirmation mode — click Cancel
		await fireEvent.click(screen.getByRole('button', { name: /cancel/i }));

		// Should be back to the initial selection view
		expect(screen.getByRole('button', { name: /pass the torch/i })).toBeInTheDocument();
		expect(screen.queryByRole('button', { name: /yes, transfer ownership/i })).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// directTransfer call and onTransferred callback
// ---------------------------------------------------------------------------

describe('PassTheTorch — directTransfer call and onTransferred callback', () => {
	it('calls directTransfer with topicId and the selected member id after confirmation', async () => {
		vi.mocked(directTransfer).mockResolvedValue(undefined);
		const onTransferred = vi.fn();

		render(PassTheTorch, {
			props: { members: [adminA, adminB], onTransferred }
		});

		// Select adminB
		const select = screen.getByRole('combobox');
		await fireEvent.change(select, { target: { value: adminB.id } });

		// Click "Pass the Torch" to open confirmation
		await fireEvent.click(screen.getByRole('button', { name: /pass the torch/i }));

		// Confirm
		await fireEvent.click(screen.getByRole('button', { name: /yes, transfer ownership/i }));

		expect(directTransfer).toHaveBeenCalledOnce();
		expect(directTransfer).toHaveBeenCalledWith('topic-1', adminB.id);
	});

	it('fires the onTransferred callback after a successful directTransfer', async () => {
		vi.mocked(directTransfer).mockResolvedValue(undefined);
		const onTransferred = vi.fn();

		render(PassTheTorch, {
			props: { members: [adminA], onTransferred }
		});

		const select = screen.getByRole('combobox');
		await fireEvent.change(select, { target: { value: adminA.id } });
		await fireEvent.click(screen.getByRole('button', { name: /pass the torch/i }));

		const confirmBtn = screen.getByRole('button', { name: /yes, transfer ownership/i });
		await fireEvent.click(confirmBtn);

		// Wait for the async handler to resolve
		await vi.waitFor(() => {
			expect(onTransferred).toHaveBeenCalledOnce();
		});
	});

	it('shows an error message and returns to selection view when directTransfer throws', async () => {
		vi.mocked(directTransfer).mockRejectedValue(new Error('Transfer failed'));
		const onTransferred = vi.fn();

		render(PassTheTorch, {
			props: { members: [adminA], onTransferred }
		});

		const select = screen.getByRole('combobox');
		await fireEvent.change(select, { target: { value: adminA.id } });
		await fireEvent.click(screen.getByRole('button', { name: /pass the torch/i }));
		await fireEvent.click(screen.getByRole('button', { name: /yes, transfer ownership/i }));

		// Error message should appear
		const error = await screen.findByText(/transfer failed/i);
		expect(error).toBeInTheDocument();

		// onTransferred must NOT have been called
		expect(onTransferred).not.toHaveBeenCalled();

		// Should be back to the selection step (confirming is reset to false)
		expect(screen.queryByRole('button', { name: /yes, transfer ownership/i })).toBeNull();
	});
});
