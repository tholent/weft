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
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { http, HttpResponse } from 'msw';
import UpdateModal from '$lib/components/UpdateModal.svelte';
import { makeUpdate, makeCircle, makeReply } from '../fixtures';
import { server } from '../mocks/msw-server';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Register a default replies handler returning an empty list. */
function handleRepliesEmpty(topicId = 'topic-1', updateId = 'update-1') {
	server.use(
		http.get(`http://localhost/api/topics/${topicId}/updates/${updateId}/replies`, () =>
			HttpResponse.json({ items: [] })
		)
	);
}

/** Default minimal props for most tests. */
function defaultProps(overrides: Record<string, unknown> = {}) {
	return {
		update: makeUpdate({ id: 'update-1' }),
		circles: [],
		isModerator: false,
		canEdit: false,
		topicId: 'topic-1',
		onClose: vi.fn(),
		onUpdate: vi.fn(),
		...overrides
	};
}

// ---------------------------------------------------------------------------
// Full body rendering
// ---------------------------------------------------------------------------

describe('UpdateModal — full body rendering', () => {
	it('renders the complete body text without truncation', async () => {
		handleRepliesEmpty();
		const longBody = 'A'.repeat(500);
		const update = makeUpdate({ id: 'update-1', body: longBody });
		render(UpdateModal, { props: { ...defaultProps(), update } });

		// The entire 500-character body must be present in the DOM.
		await waitFor(() => {
			const bodyEl = document.querySelector('.body') as HTMLElement;
			expect(bodyEl).not.toBeNull();
			expect(bodyEl.textContent).toBe(longBody);
		});
	});

	it('renders the exact update body string', async () => {
		handleRepliesEmpty();
		const body = 'This is the exact update body content for modal display.';
		const update = makeUpdate({ id: 'update-1', body });
		render(UpdateModal, { props: { ...defaultProps(), update } });

		await waitFor(() => {
			expect(screen.getByText(body)).toBeInTheDocument();
		});
	});

	it('shows the author handle when present', async () => {
		handleRepliesEmpty();
		const update = makeUpdate({ id: 'update-1', author_handle: 'alice' });
		render(UpdateModal, { props: { ...defaultProps(), update } });

		await waitFor(() => {
			expect(screen.getByText('alice')).toBeInTheDocument();
		});
	});

	it('shows "Anonymous" when author_handle is null', async () => {
		handleRepliesEmpty();
		const update = makeUpdate({ id: 'update-1', author_handle: null });
		render(UpdateModal, { props: { ...defaultProps(), update } });

		await waitFor(() => {
			expect(screen.getByText('Anonymous')).toBeInTheDocument();
		});
	});
});

// ---------------------------------------------------------------------------
// Edit mode gated on canEdit
// ---------------------------------------------------------------------------

describe('UpdateModal — edit mode visibility', () => {
	it('does NOT show an Edit button when canEdit is false', async () => {
		handleRepliesEmpty();
		render(UpdateModal, { props: defaultProps({ canEdit: false }) });

		// Allow mount + reply load to settle before asserting absence.
		await waitFor(() => {
			expect(screen.queryByRole('button', { name: /edit/i })).toBeNull();
		});
	});

	it('shows an Edit button when canEdit is true', async () => {
		handleRepliesEmpty();
		render(UpdateModal, { props: defaultProps({ canEdit: true }) });

		await waitFor(() => {
			expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
		});
	});

	it('clicking Edit reveals a textarea with the current body', async () => {
		handleRepliesEmpty();
		const body = 'Editable content here';
		const update = makeUpdate({ id: 'update-1', body });
		render(UpdateModal, { props: { ...defaultProps({ canEdit: true }), update } });

		const editBtn = await screen.findByRole('button', { name: /edit/i });
		await fireEvent.click(editBtn);

		// After clicking, the static <p class="body"> disappears and a textarea appears.
		await waitFor(() => {
			const textarea = document.querySelector('textarea.edit-body') as HTMLTextAreaElement;
			expect(textarea).not.toBeNull();
			expect(textarea.value).toBe(body);
		});
	});

	it('clicking Cancel in edit mode hides the textarea and restores body text', async () => {
		handleRepliesEmpty();
		const body = 'Body before editing';
		const update = makeUpdate({ id: 'update-1', body });
		render(UpdateModal, { props: { ...defaultProps({ canEdit: true }), update } });

		// Enter edit mode.
		const editBtn = await screen.findByRole('button', { name: /edit/i });
		await fireEvent.click(editBtn);

		// Cancel edit mode.
		const cancelBtn = screen.getByRole('button', { name: /cancel/i });
		await fireEvent.click(cancelBtn);

		// The static body paragraph should be back.
		await waitFor(() => {
			expect(screen.getByText(body)).toBeInTheDocument();
			expect(document.querySelector('textarea.edit-body')).toBeNull();
		});
	});
});

// ---------------------------------------------------------------------------
// Delete functionality (not present in UpdateModal)
// ---------------------------------------------------------------------------

describe('UpdateModal — no delete control', () => {
	it('does not render any delete button (UpdateModal has no delete action)', async () => {
		handleRepliesEmpty();
		render(UpdateModal, { props: defaultProps() });

		await waitFor(() => {
			expect(screen.queryByRole('button', { name: /delete/i })).toBeNull();
		});
	});
});

// ---------------------------------------------------------------------------
// Replies loaded via getReplies on mount
// ---------------------------------------------------------------------------

describe('UpdateModal — replies loading', () => {
	it('calls GET /api/topics/:topicId/updates/:updateId/replies on mount and renders replies', async () => {
		const replyBody = 'the reply body';
		server.use(
			http.get('http://localhost/api/topics/:topicId/updates/:updateId/replies', () =>
				HttpResponse.json({ items: [makeReply({ body: replyBody })] })
			)
		);

		render(UpdateModal, { props: defaultProps() });

		await waitFor(() => {
			expect(screen.getByText(replyBody)).toBeInTheDocument();
		});
	});

	it('shows "No replies yet." when the replies list is empty', async () => {
		handleRepliesEmpty();
		render(UpdateModal, { props: defaultProps() });

		await waitFor(() => {
			expect(screen.getByText('No replies yet.')).toBeInTheDocument();
		});
	});

	it('shows "Replies (N)" heading reflecting the count', async () => {
		const reply1 = makeReply({ id: 'r1', body: 'First reply' });
		const reply2 = makeReply({ id: 'r2', body: 'Second reply' });
		server.use(
			http.get('http://localhost/api/topics/:topicId/updates/:updateId/replies', () =>
				HttpResponse.json({ items: [reply1, reply2] })
			)
		);

		render(UpdateModal, { props: defaultProps() });

		await waitFor(() => {
			expect(screen.getByText('Replies (2)')).toBeInTheDocument();
		});
	});

	it('passes the correct topicId and updateId to the replies endpoint', async () => {
		let capturedTopicId: string | undefined;
		let capturedUpdateId: string | undefined;

		server.use(
			http.get(
				'http://localhost/api/topics/:topicId/updates/:updateId/replies',
				({ params }) => {
					capturedTopicId = params.topicId as string;
					capturedUpdateId = params.updateId as string;
					return HttpResponse.json({ items: [] });
				}
			)
		);

		const update = makeUpdate({ id: 'update-99' });
		render(UpdateModal, {
			props: { ...defaultProps({ topicId: 'topic-42' }), update }
		});

		await waitFor(() => {
			expect(capturedTopicId).toBe('topic-42');
			expect(capturedUpdateId).toBe('update-99');
		});
	});
});

// ---------------------------------------------------------------------------
// Close behaviour
// ---------------------------------------------------------------------------

describe('UpdateModal — close behaviour', () => {
	it('calls onClose when the ✕ button is clicked', async () => {
		handleRepliesEmpty();
		const onClose = vi.fn();
		render(UpdateModal, { props: defaultProps({ onClose }) });

		const closeBtn = screen.getByRole('button', { name: '✕' });
		await fireEvent.click(closeBtn);

		expect(onClose).toHaveBeenCalledOnce();
	});

	it('calls onClose when Escape is pressed', async () => {
		handleRepliesEmpty();
		const onClose = vi.fn();
		render(UpdateModal, { props: defaultProps({ onClose }) });

		await fireEvent.keyDown(window, { key: 'Escape' });

		expect(onClose).toHaveBeenCalledOnce();
	});
});

// ---------------------------------------------------------------------------
// Circle pills
// ---------------------------------------------------------------------------

describe('UpdateModal — circle pills', () => {
	it('renders circle name pills for each circle in circle_ids', async () => {
		server.use(
			http.get('http://localhost/api/topics/topic-1/updates/update-1/replies', () =>
				HttpResponse.json({ items: [] })
			)
		);
		const circles = [
			makeCircle({ id: 'c1', name: 'Friends' }),
			makeCircle({ id: 'c2', name: 'Family' })
		];
		const update = makeUpdate({ id: 'update-1', circle_ids: ['c1', 'c2'] });
		render(UpdateModal, {
			props: { update, circles, isModerator: false, canEdit: false, topicId: 'topic-1', onClose: vi.fn() }
		});

		await waitFor(() => {
			expect(screen.getByText('Friends')).toBeInTheDocument();
			expect(screen.getByText('Family')).toBeInTheDocument();
		});
	});

	it('renders no pills when circle_ids is empty', async () => {
		handleRepliesEmpty();
		const update = makeUpdate({ id: 'update-1', circle_ids: [] });
		render(UpdateModal, { props: { ...defaultProps(), update } });

		await waitFor(() => {
			expect(document.querySelectorAll('.pill')).toHaveLength(0);
		});
	});
});

// ---------------------------------------------------------------------------
// Moderator compose box visibility
// ---------------------------------------------------------------------------

describe('UpdateModal — moderator compose box', () => {
	it('shows the Reply compose box when isModerator is true', async () => {
		handleRepliesEmpty();
		render(UpdateModal, { props: defaultProps({ isModerator: true }) });

		await waitFor(() => {
			expect(screen.getByPlaceholderText('Write a reply…')).toBeInTheDocument();
		});
	});

	it('does not show the Reply compose box when isModerator is false', async () => {
		handleRepliesEmpty();
		render(UpdateModal, { props: defaultProps({ isModerator: false }) });

		await waitFor(() => {
			expect(screen.queryByPlaceholderText('Write a reply…')).toBeNull();
		});
	});
});
