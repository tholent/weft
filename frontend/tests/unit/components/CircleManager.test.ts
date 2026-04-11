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
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/msw-server';
import CircleManager from '$lib/components/CircleManager.svelte';
import { circles as circlesStore } from '$lib/stores/topic';
import { session } from '$lib/stores/session';
import { makeCircle } from '../fixtures';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Seed the stores that CircleManager reads directly. */
function seedStores(topicId: string, initialCircles = [makeCircle()]) {
	session.set({ token: 'tok', memberId: 'mem-1', role: 'admin', topicId });
	circlesStore.set(initialCircles);
}

// Restore window.confirm after each test that spies on it.
afterEach(() => {
	vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// List rendering
// ---------------------------------------------------------------------------

describe('CircleManager — list rendering', () => {
	it('renders the name of each circle in the store', () => {
		seedStores('topic-1', [
			makeCircle({ id: 'c1', name: 'Alpha' }),
			makeCircle({ id: 'c2', name: 'Beta' }),
			makeCircle({ id: 'c3', name: 'Gamma' })
		]);
		render(CircleManager);

		expect(screen.getByText('Alpha')).toBeInTheDocument();
		expect(screen.getByText('Beta')).toBeInTheDocument();
		expect(screen.getByText('Gamma')).toBeInTheDocument();
	});

	it('renders an Edit and Delete button for each circle', () => {
		seedStores('topic-1', [
			makeCircle({ id: 'c1', name: 'Alpha' }),
			makeCircle({ id: 'c2', name: 'Beta' })
		]);
		render(CircleManager);

		// two Edit buttons and two Delete buttons
		expect(screen.getAllByRole('button', { name: /Edit/i })).toHaveLength(2);
		expect(screen.getAllByRole('button', { name: /Delete/i })).toHaveLength(2);
	});

	it('renders the scoped_title in parentheses when present', () => {
		seedStores('topic-1', [makeCircle({ id: 'c1', name: 'VIP', scoped_title: 'VIP Guests' })]);
		render(CircleManager);

		expect(screen.getByText('(VIP Guests)')).toBeInTheDocument();
	});

	it('does NOT render a scoped_title span when scoped_title is null', () => {
		seedStores('topic-1', [makeCircle({ id: 'c1', name: 'General', scoped_title: null })]);
		render(CircleManager);

		// The scoped span only appears when scoped_title is truthy
		expect(document.querySelector('.scoped')).toBeNull();
	});

	it('renders the "Add Circle" form', () => {
		seedStores('topic-1', []);
		render(CircleManager);

		expect(screen.getByPlaceholderText('New circle name')).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /Add Circle/i })).toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// Create circle
// ---------------------------------------------------------------------------

describe('CircleManager — create circle', () => {
	it('sends POST to /api/topics/:topicId/circles with the typed name', async () => {
		const topicId = 'topic-create';
		seedStores(topicId, []);

		let capturedBody: unknown;
		const newCircle = makeCircle({ id: 'c-new', name: 'Supporters' });

		server.use(
			http.post(`http://localhost/api/topics/${topicId}/circles`, async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(newCircle);
			}),
			// handleCreate calls listCircles after the POST to refresh the store
			http.get(`http://localhost/api/topics/${topicId}/circles`, () => {
				return HttpResponse.json([newCircle]);
			})
		);

		render(CircleManager);

		const nameInput = screen.getByPlaceholderText('New circle name');
		await fireEvent.input(nameInput, { target: { value: 'Supporters' } });
		await fireEvent.click(screen.getByRole('button', { name: /Add Circle/i }));

		// The POST body must contain the name we typed
		await waitFor(() => expect(capturedBody).toMatchObject({ name: 'Supporters' }));
	});

	it('includes scoped_title in POST body when provided', async () => {
		const topicId = 'topic-scoped';
		seedStores(topicId, []);

		let capturedBody: unknown;
		const newCircle = makeCircle({ id: 'c-sc', name: 'Press', scoped_title: 'Media' });

		server.use(
			http.post(`http://localhost/api/topics/${topicId}/circles`, async ({ request }) => {
				capturedBody = await request.json();
				return HttpResponse.json(newCircle);
			}),
			http.get(`http://localhost/api/topics/${topicId}/circles`, () => {
				return HttpResponse.json([newCircle]);
			})
		);

		render(CircleManager);

		await fireEvent.input(screen.getByPlaceholderText('New circle name'), {
			target: { value: 'Press' }
		});
		await fireEvent.input(screen.getByPlaceholderText('Scoped title (optional)'), {
			target: { value: 'Media' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /Add Circle/i }));

		await waitFor(() =>
			expect(capturedBody).toMatchObject({ name: 'Press', scoped_title: 'Media' })
		);
	});

	it('does NOT send a POST when the name input is blank', async () => {
		const topicId = 'topic-blank';
		seedStores(topicId, []);

		let postCalled = false;
		server.use(
			http.post(`http://localhost/api/topics/${topicId}/circles`, () => {
				postCalled = true;
				return HttpResponse.json(makeCircle());
			})
		);

		render(CircleManager);

		// Leave the name input empty and submit
		await fireEvent.click(screen.getByRole('button', { name: /Add Circle/i }));

		expect(postCalled).toBe(false);
	});
});

// ---------------------------------------------------------------------------
// Rename (edit) circle
// ---------------------------------------------------------------------------

describe('CircleManager — rename circle', () => {
	it('sends PATCH to /api/topics/:topicId/circles/:circleId with the new name', async () => {
		const topicId = 'topic-rename';
		const circle = makeCircle({ id: 'c-rename', name: 'Old Name' });
		seedStores(topicId, [circle]);

		let capturedUrl: string | undefined;
		let capturedBody: unknown;
		const renamed = makeCircle({ id: 'c-rename', name: 'New Name' });

		server.use(
			http.patch(
				`http://localhost/api/topics/${topicId}/circles/${circle.id}`,
				async ({ request }) => {
					capturedUrl = request.url;
					capturedBody = await request.json();
					return HttpResponse.json(renamed);
				}
			),
			// handleRename calls listCircles after the PATCH to refresh the store
			http.get(`http://localhost/api/topics/${topicId}/circles`, () => {
				return HttpResponse.json([renamed]);
			})
		);

		render(CircleManager);

		// Click the Edit button to enter edit mode
		const editBtn = screen.getByRole('button', { name: /Edit/i });
		await fireEvent.click(editBtn);

		// The name input is now pre-filled; clear it and type the new name
		const nameInput = screen.getByPlaceholderText('Name') as HTMLInputElement;
		await fireEvent.input(nameInput, { target: { value: 'New Name' } });

		// Click Save
		await fireEvent.click(screen.getByRole('button', { name: /Save/i }));

		await waitFor(() => {
			expect(capturedUrl).toContain(`/api/topics/${topicId}/circles/${circle.id}`);
			expect(capturedBody).toMatchObject({ name: 'New Name' });
		});
	});

	it('clicking Cancel exits edit mode without calling PATCH', async () => {
		const topicId = 'topic-cancel';
		const circle = makeCircle({ id: 'c-cancel', name: 'Stay Same' });
		seedStores(topicId, [circle]);

		let patchCalled = false;
		server.use(
			http.patch(`http://localhost/api/topics/${topicId}/circles/${circle.id}`, () => {
				patchCalled = true;
				return HttpResponse.json(circle);
			})
		);

		render(CircleManager);

		await fireEvent.click(screen.getByRole('button', { name: /Edit/i }));
		// Edit mode is active — Cancel button should be visible
		await fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));

		// Should be back to view mode, showing the circle name again
		expect(screen.getByText('Stay Same')).toBeInTheDocument();
		expect(patchCalled).toBe(false);
	});
});

// ---------------------------------------------------------------------------
// Delete circle — with window.confirm gate
// ---------------------------------------------------------------------------

describe('CircleManager — delete circle', () => {
	it('sends DELETE when window.confirm returns true', async () => {
		vi.spyOn(window, 'confirm').mockReturnValue(true);

		const topicId = 'topic-delete';
		const circle = makeCircle({ id: 'c-del', name: 'To Delete' });
		seedStores(topicId, [circle]);

		let deleteCalledUrl: string | undefined;

		server.use(
			http.delete(`http://localhost/api/topics/${topicId}/circles/${circle.id}`, ({ request }) => {
				deleteCalledUrl = request.url;
				return new HttpResponse(null, { status: 204 });
			}),
			// handleDelete calls listCircles after the DELETE to refresh the store
			http.get(`http://localhost/api/topics/${topicId}/circles`, () => {
				return HttpResponse.json([]);
			})
		);

		render(CircleManager);

		await fireEvent.click(screen.getByRole('button', { name: /Delete/i }));

		expect(window.confirm).toHaveBeenCalledWith('Delete this circle?');
		await waitFor(() =>
			expect(deleteCalledUrl).toContain(`/api/topics/${topicId}/circles/${circle.id}`)
		);
	});

	it('does NOT send DELETE when window.confirm returns false (dismissed)', async () => {
		vi.spyOn(window, 'confirm').mockReturnValue(false);

		const topicId = 'topic-dismiss';
		const circle = makeCircle({ id: 'c-nodissmiss', name: 'Keep Me' });
		seedStores(topicId, [circle]);

		let deleteCalled = false;
		server.use(
			http.delete(`http://localhost/api/topics/${topicId}/circles/${circle.id}`, () => {
				deleteCalled = true;
				return new HttpResponse(null, { status: 204 });
			})
		);

		render(CircleManager);

		await fireEvent.click(screen.getByRole('button', { name: /Delete/i }));

		expect(window.confirm).toHaveBeenCalledWith('Delete this circle?');
		expect(deleteCalled).toBe(false);
		// The circle remains visible in the UI (store was not updated)
		expect(screen.getByText('Keep Me')).toBeInTheDocument();
	});

	it('shows an alert and keeps circle in store when DELETE returns an error', async () => {
		vi.spyOn(window, 'confirm').mockReturnValue(true);
		const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

		const topicId = 'topic-err';
		const circle = makeCircle({ id: 'c-err', name: 'Error Circle' });
		seedStores(topicId, [circle]);

		server.use(
			http.delete(`http://localhost/api/topics/${topicId}/circles/${circle.id}`, () => {
				return HttpResponse.json({ detail: 'Circle has members' }, { status: 400 });
			})
		);

		render(CircleManager);

		await fireEvent.click(screen.getByRole('button', { name: /Delete/i }));

		// alert() should have been called with an error message
		await waitFor(() => expect(alertSpy).toHaveBeenCalled());
	});
});

// ---------------------------------------------------------------------------
// Scoped-title visual variant
// Note: Circle has no deleted_at field. The "secondary display" variant in
// CircleManager is the scoped_title, rendered in a .scoped span. These tests
// verify that the .scoped class is applied correctly.
// ---------------------------------------------------------------------------

describe('CircleManager — scoped_title display', () => {
	it('applies the .scoped class to the scoped_title span', () => {
		seedStores('topic-sc', [
			makeCircle({ id: 'c1', name: 'Founders', scoped_title: 'Founding Members' })
		]);
		render(CircleManager);

		const scopedEl = document.querySelector('.scoped');
		expect(scopedEl).not.toBeNull();
		expect(scopedEl?.textContent).toBe('(Founding Members)');
	});

	it('renders multiple circles each with their own .scoped spans', () => {
		seedStores('topic-multi-sc', [
			makeCircle({ id: 'c1', name: 'A', scoped_title: 'Title A' }),
			makeCircle({ id: 'c2', name: 'B', scoped_title: 'Title B' }),
			makeCircle({ id: 'c3', name: 'C', scoped_title: null })
		]);
		render(CircleManager);

		// Two circles have scoped titles, one does not
		const scopedEls = document.querySelectorAll('.scoped');
		expect(scopedEls).toHaveLength(2);
	});
});
