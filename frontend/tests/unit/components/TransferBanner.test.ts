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
import TransferBanner from '$lib/components/TransferBanner.svelte';
import { session } from '$lib/stores/session';

vi.mock('$lib/api/transfer', () => ({
	getTransferStatus: vi.fn(),
	requestTransfer: vi.fn(),
	cancelTransfer: vi.fn(),
	directTransfer: vi.fn()
}));

import { getTransferStatus, cancelTransfer, requestTransfer } from '$lib/api/transfer';

// A future deadline for use in pending transfer fixtures
const FUTURE_DEADLINE = new Date(Date.now() + 3_600_000).toISOString();

// ---------------------------------------------------------------------------
// Hidden when absent
// ---------------------------------------------------------------------------

describe('TransferBanner — hidden when absent', () => {
	beforeEach(() => {
		session.set({ token: 'tok', memberId: 'm1', role: 'admin', topicId: 'topic-1' });
	});

	it('renders nothing meaningful when getTransferStatus returns null', async () => {
		vi.mocked(getTransferStatus).mockResolvedValue(null);

		render(TransferBanner);

		// Wait for onMount to complete
		await screen.findByText(/request creator transfer/i);

		// The pending block must not be present
		expect(screen.queryByText(/creator transfer pending/i)).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Pending display
// ---------------------------------------------------------------------------

describe('TransferBanner — pending display', () => {
	beforeEach(() => {
		session.set({ token: 'tok', memberId: 'm1', role: 'owner', topicId: 'topic-1' });
	});

	it('shows the pending transfer message when a pending transfer exists', async () => {
		vi.mocked(getTransferStatus).mockResolvedValue({
			id: 'xfer-1',
			status: 'pending',
			deadline: FUTURE_DEADLINE,
			created_at: new Date().toISOString()
		});

		render(TransferBanner);

		const msg = await screen.findByText(/creator transfer pending/i);
		expect(msg).toBeInTheDocument();
	});

	it('shows a time-remaining indicator in the pending message', async () => {
		vi.mocked(getTransferStatus).mockResolvedValue({
			id: 'xfer-2',
			status: 'pending',
			deadline: FUTURE_DEADLINE,
			created_at: new Date().toISOString()
		});

		render(TransferBanner);

		// The countdown renders something like "1h 0m remaining"
		const msg = await screen.findByText(/remaining/i);
		expect(msg).toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// Cancel action — owner can cancel
// ---------------------------------------------------------------------------

describe('TransferBanner — cancel action', () => {
	beforeEach(() => {
		// Owner can see and use the cancel button
		session.set({ token: 'tok', memberId: 'm1', role: 'owner', topicId: 'topic-1' });
	});

	it('shows "Cancel Transfer" button when the viewer is the owner and a transfer is pending', async () => {
		vi.mocked(getTransferStatus).mockResolvedValue({
			id: 'xfer-3',
			status: 'pending',
			deadline: FUTURE_DEADLINE,
			created_at: new Date().toISOString()
		});

		render(TransferBanner);

		const cancelBtn = await screen.findByRole('button', { name: /cancel transfer/i });
		expect(cancelBtn).toBeInTheDocument();
	});

	it('calls cancelTransfer with the topicId when the cancel button is clicked', async () => {
		vi.mocked(getTransferStatus).mockResolvedValue({
			id: 'xfer-4',
			status: 'pending',
			deadline: FUTURE_DEADLINE,
			created_at: new Date().toISOString()
		});
		vi.mocked(cancelTransfer).mockResolvedValue(undefined);

		render(TransferBanner);

		const cancelBtn = await screen.findByRole('button', { name: /cancel transfer/i });
		await fireEvent.click(cancelBtn);

		expect(cancelTransfer).toHaveBeenCalledWith('topic-1');
	});

	it('hides the pending message after the cancel resolves', async () => {
		vi.mocked(getTransferStatus).mockResolvedValue({
			id: 'xfer-5',
			status: 'pending',
			deadline: FUTURE_DEADLINE,
			created_at: new Date().toISOString()
		});
		vi.mocked(cancelTransfer).mockResolvedValue(undefined);

		render(TransferBanner);

		const cancelBtn = await screen.findByRole('button', { name: /cancel transfer/i });
		await fireEvent.click(cancelBtn);

		// After cancellation, the pending block should be gone
		expect(screen.queryByText(/creator transfer pending/i)).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Owner vs admin view differences
// ---------------------------------------------------------------------------

describe('TransferBanner — owner vs admin view differences', () => {
	it('shows "Cancel Transfer" button for owner when transfer is pending', async () => {
		session.set({ token: 'tok', memberId: 'm1', role: 'owner', topicId: 'topic-1' });

		vi.mocked(getTransferStatus).mockResolvedValue({
			id: 'xfer-6',
			status: 'pending',
			deadline: FUTURE_DEADLINE,
			created_at: new Date().toISOString()
		});

		render(TransferBanner);

		await screen.findByText(/creator transfer pending/i);
		expect(screen.getByRole('button', { name: /cancel transfer/i })).toBeInTheDocument();
	});

	it('does NOT show "Cancel Transfer" button for admin when transfer is pending', async () => {
		// Admin (non-owner) sees the pending status but cannot cancel
		session.set({ token: 'tok', memberId: 'm2', role: 'admin', topicId: 'topic-1' });

		vi.mocked(getTransferStatus).mockResolvedValue({
			id: 'xfer-7',
			status: 'pending',
			deadline: FUTURE_DEADLINE,
			created_at: new Date().toISOString()
		});

		render(TransferBanner);

		await screen.findByText(/creator transfer pending/i);
		expect(screen.queryByRole('button', { name: /cancel transfer/i })).toBeNull();
	});

	it('shows "Request Creator Transfer" button for admin (non-owner) when no transfer is pending', async () => {
		session.set({ token: 'tok', memberId: 'm2', role: 'admin', topicId: 'topic-1' });

		vi.mocked(getTransferStatus).mockResolvedValue(null);

		render(TransferBanner);

		const requestBtn = await screen.findByRole('button', { name: /request creator transfer/i });
		expect(requestBtn).toBeInTheDocument();
	});

	it('does NOT show "Request Creator Transfer" button for owner', async () => {
		session.set({ token: 'tok', memberId: 'm1', role: 'owner', topicId: 'topic-1' });

		vi.mocked(getTransferStatus).mockResolvedValue(null);

		render(TransferBanner);

		// Owners don't see the request button — they ARE the owner.
		// Wait for onMount to complete by polling; the request button must remain absent.
		await vi.waitFor(() => {
			// getTransferStatus should have been called once onMount fires
			expect(getTransferStatus).toHaveBeenCalled();
		});

		expect(screen.queryByRole('button', { name: /request creator transfer/i })).toBeNull();
	});

	it('calls requestTransfer with the topicId when admin clicks the request button', async () => {
		session.set({ token: 'tok', memberId: 'm2', role: 'admin', topicId: 'topic-1' });

		vi.mocked(getTransferStatus).mockResolvedValue(null);
		vi.mocked(requestTransfer).mockResolvedValue({
			id: 'xfer-8',
			status: 'pending',
			deadline: FUTURE_DEADLINE,
			created_at: new Date().toISOString()
		});

		render(TransferBanner);

		const requestBtn = await screen.findByRole('button', { name: /request creator transfer/i });
		await fireEvent.click(requestBtn);

		expect(requestTransfer).toHaveBeenCalledWith('topic-1');
	});
});
