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
import ComposeBox from '$lib/components/ComposeBox.svelte';
import { makeCircle } from '../fixtures';

// ---------------------------------------------------------------------------
// Mode switching: update vs reply
// ---------------------------------------------------------------------------

describe('ComposeBox — mode switching', () => {
	it('renders a photo button in update mode', () => {
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [makeCircle()],
				onSubmit: vi.fn()
			}
		});

		// Photo button is only rendered in update mode
		expect(screen.getByTitle(/Attach photos|Maximum \d+ photos/)).toBeInTheDocument();
	});

	it('renders "Share with group" checkbox in reply mode', () => {
		render(ComposeBox, {
			props: {
				mode: 'reply',
				targetCircles: [],
				onSubmit: vi.fn()
			}
		});

		expect(screen.getByText(/Share with group/)).toBeInTheDocument();
	});

	it('does NOT render "Share with group" in update mode', () => {
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [],
				onSubmit: vi.fn()
			}
		});

		expect(screen.queryByText(/Share with group/)).toBeNull();
	});

	it('does NOT render a photo button in reply mode', () => {
		render(ComposeBox, {
			props: {
				mode: 'reply',
				targetCircles: [],
				onSubmit: vi.fn()
			}
		});

		expect(screen.queryByTitle(/Attach photos|Maximum \d+ photos/)).toBeNull();
	});

	it('renders a scope select in mod_response mode', () => {
		render(ComposeBox, {
			props: {
				mode: 'mod_response',
				targetCircles: [],
				onSubmit: vi.fn()
			}
		});

		expect(screen.getByRole('combobox')).toBeInTheDocument();
		expect(screen.getByText('Sender only')).toBeInTheDocument();
	});

	it('renders circle pills in update mode when targetCircles are provided', () => {
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [makeCircle({ id: 'c1', name: 'Alpha' })],
				onSubmit: vi.fn()
			}
		});

		expect(screen.getByText('Alpha')).toBeInTheDocument();
	});

	it('does NOT render circle pills in reply mode', () => {
		render(ComposeBox, {
			props: {
				mode: 'reply',
				targetCircles: [makeCircle({ id: 'c1', name: 'Alpha' })],
				onSubmit: vi.fn()
			}
		});

		// In reply mode the circle pills section is not rendered
		expect(screen.queryByText('Alpha')).toBeNull();
	});

	it('uses "Write an update…" placeholder in update mode with no custom messages', () => {
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [],
				onSubmit: vi.fn()
			}
		});

		const textarea = screen.getByRole('textbox');
		expect(textarea).toHaveAttribute('placeholder', 'Write an update…');
	});

	it('uses "Write a reply…" placeholder in reply mode', () => {
		render(ComposeBox, {
			props: {
				mode: 'reply',
				targetCircles: [],
				onSubmit: vi.fn()
			}
		});

		const textarea = screen.getByRole('textbox');
		expect(textarea).toHaveAttribute('placeholder', 'Write a reply…');
	});
});

// ---------------------------------------------------------------------------
// Submit button disabled state
// ---------------------------------------------------------------------------

describe('ComposeBox — submit button', () => {
	it('send button is present and not disabled when body is empty (guard is in handleSubmit)', () => {
		// The Send button is only disabled when uploading. Empty body is guarded
		// inside handleSubmit() by an early return, not by the disabled attribute.
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [],
				onSubmit: vi.fn()
			}
		});

		const send = screen.getByRole('button', { name: /Send/i });
		expect(send).not.toBeDisabled();
	});

	it('does NOT call onSubmit when body is empty and form is submitted', async () => {
		const onSubmit = vi.fn();
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [],
				onSubmit
			}
		});

		const send = screen.getByRole('button', { name: /Send/i });
		await fireEvent.click(send);

		expect(onSubmit).not.toHaveBeenCalled();
	});

	it('does NOT call onSubmit in reply mode when body is empty', async () => {
		const onSubmit = vi.fn();
		render(ComposeBox, {
			props: {
				mode: 'reply',
				targetCircles: [],
				onSubmit
			}
		});

		const send = screen.getByRole('button', { name: /Send/i });
		await fireEvent.click(send);

		expect(onSubmit).not.toHaveBeenCalled();
	});
});

// ---------------------------------------------------------------------------
// Submit enabled and payload shape — update mode
// ---------------------------------------------------------------------------

describe('ComposeBox — update mode onSubmit payload', () => {
	it('calls onSubmit with body, circle_ids, and circle_bodies when body is filled', async () => {
		const onSubmit = vi.fn().mockResolvedValue({ id: 'u1' });
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [makeCircle({ id: 'c1', name: 'Alpha' })],
				onSubmit
			}
		});

		const textarea = screen.getByRole('textbox');
		await fireEvent.input(textarea, { target: { value: 'Hello world' } });

		const send = screen.getByRole('button', { name: /Send/i });
		await fireEvent.click(send);

		expect(onSubmit).toHaveBeenCalledOnce();
		const payload = onSubmit.mock.calls[0][0] as Record<string, unknown>;
		expect(payload).toHaveProperty('body', 'Hello world');
		expect(payload).toHaveProperty('circle_ids');
		expect(payload).toHaveProperty('circle_bodies');
	});

	it('includes all targetCircle ids in circle_ids when no circles are explicitly selected', async () => {
		const onSubmit = vi.fn().mockResolvedValue({ id: 'u1' });
		const circles = [
			makeCircle({ id: 'c1', name: 'Alpha' }),
			makeCircle({ id: 'c2', name: 'Beta' })
		];
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: circles,
				onSubmit
			}
		});

		const textarea = screen.getByRole('textbox');
		await fireEvent.input(textarea, { target: { value: 'Broadcast' } });

		await fireEvent.click(screen.getByRole('button', { name: /Send/i }));

		const payload = onSubmit.mock.calls[0][0] as Record<string, unknown>;
		expect(payload.circle_ids).toEqual(['c1', 'c2']);
	});

	it('includes only selected circle ids when circles have been toggled', async () => {
		const onSubmit = vi.fn().mockResolvedValue({ id: 'u1' });
		const circles = [
			makeCircle({ id: 'c1', name: 'Alpha' }),
			makeCircle({ id: 'c2', name: 'Beta' })
		];
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: circles,
				onSubmit
			}
		});

		// Select only Beta
		await fireEvent.click(screen.getByText('Beta'));

		const textarea = screen.getByRole('textbox');
		await fireEvent.input(textarea, { target: { value: 'Targeted' } });

		await fireEvent.click(screen.getByRole('button', { name: /Send/i }));

		const payload = onSubmit.mock.calls[0][0] as Record<string, unknown>;
		expect(payload.circle_ids).toEqual(['c2']);
	});

	it('resets the body textarea to empty after a successful submit', async () => {
		const onSubmit = vi.fn().mockResolvedValue({ id: 'u1' });
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [],
				onSubmit
			}
		});

		const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
		await fireEvent.input(textarea, { target: { value: 'Some text' } });
		await fireEvent.click(screen.getByRole('button', { name: /Send/i }));

		expect(textarea.value).toBe('');
	});
});

// ---------------------------------------------------------------------------
// Submit payload shape — reply mode
// ---------------------------------------------------------------------------

describe('ComposeBox — reply mode onSubmit payload', () => {
	it('calls onSubmit with body and wants_to_share=false by default', async () => {
		const onSubmit = vi.fn();
		render(ComposeBox, {
			props: {
				mode: 'reply',
				targetCircles: [],
				onSubmit
			}
		});

		const textarea = screen.getByRole('textbox');
		await fireEvent.input(textarea, { target: { value: 'My reply' } });
		await fireEvent.click(screen.getByRole('button', { name: /Send/i }));

		expect(onSubmit).toHaveBeenCalledOnce();
		const payload = onSubmit.mock.calls[0][0] as Record<string, unknown>;
		expect(payload).toEqual({ body: 'My reply', wants_to_share: false });
	});

	it('calls onSubmit with wants_to_share=true when checkbox is checked', async () => {
		const onSubmit = vi.fn();
		render(ComposeBox, {
			props: {
				mode: 'reply',
				targetCircles: [],
				onSubmit
			}
		});

		const textarea = screen.getByRole('textbox');
		await fireEvent.input(textarea, { target: { value: 'Share this' } });

		const checkbox = screen.getByRole('checkbox');
		await fireEvent.click(checkbox);

		await fireEvent.click(screen.getByRole('button', { name: /Send/i }));

		const payload = onSubmit.mock.calls[0][0] as Record<string, unknown>;
		expect(payload).toEqual({ body: 'Share this', wants_to_share: true });
	});
});

// ---------------------------------------------------------------------------
// Submit payload shape — mod_response mode
// ---------------------------------------------------------------------------

describe('ComposeBox — mod_response mode onSubmit payload', () => {
	it('calls onSubmit with body and scope=sender_only by default', async () => {
		const onSubmit = vi.fn();
		render(ComposeBox, {
			props: {
				mode: 'mod_response',
				targetCircles: [],
				onSubmit
			}
		});

		const textarea = screen.getByRole('textbox');
		await fireEvent.input(textarea, { target: { value: 'Mod note' } });
		await fireEvent.click(screen.getByRole('button', { name: /Send/i }));

		expect(onSubmit).toHaveBeenCalledOnce();
		const payload = onSubmit.mock.calls[0][0] as Record<string, unknown>;
		expect(payload).toEqual({ body: 'Mod note', scope: 'sender_only' });
	});
});

// ---------------------------------------------------------------------------
// Per-circle body variant inputs
// ---------------------------------------------------------------------------

describe('ComposeBox — per-circle body variants', () => {
	it('does NOT render a custom variant textarea before any circle is selected', () => {
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [makeCircle({ id: 'c1', name: 'Alpha' })],
				onSubmit: vi.fn()
			}
		});

		// Only the main body textarea should be present initially
		expect(screen.getAllByRole('textbox')).toHaveLength(1);
	});

	it('does NOT render a custom variant textarea after selecting a circle (before clicking ALT)', async () => {
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [makeCircle({ id: 'c1', name: 'Alpha' })],
				onSubmit: vi.fn()
			}
		});

		// Select the circle
		await fireEvent.click(screen.getByText('Alpha'));

		// Still only the main textarea — variant textarea requires ALT button click
		expect(screen.getAllByRole('textbox')).toHaveLength(1);
	});

	it('renders a custom variant textarea after selecting a circle AND clicking ALT', async () => {
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [makeCircle({ id: 'c1', name: 'Alpha' })],
				onSubmit: vi.fn()
			}
		});

		// Select the circle to make the ALT button appear
		await fireEvent.click(screen.getByText('Alpha'));

		// Click the ALT button to enable the custom variant
		const altBtn = screen.getByTitle('Custom message for Alpha');
		await fireEvent.click(altBtn);

		// Now there should be a second textarea (the variant textarea)
		expect(screen.getAllByRole('textbox')).toHaveLength(2);
	});

	it('renders one variant textarea per circle with ALT enabled', async () => {
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [
					makeCircle({ id: 'c1', name: 'Alpha' }),
					makeCircle({ id: 'c2', name: 'Beta' })
				],
				onSubmit: vi.fn()
			}
		});

		// Select both circles
		await fireEvent.click(screen.getByText('Alpha'));
		await fireEvent.click(screen.getByText('Beta'));

		// Enable ALT for both
		await fireEvent.click(screen.getByTitle('Custom message for Alpha'));
		await fireEvent.click(screen.getByTitle('Custom message for Beta'));

		// Main textarea + 2 variant textareas
		expect(screen.getAllByRole('textbox')).toHaveLength(3);
	});

	it('includes custom body in circle_bodies when ALT is enabled and filled', async () => {
		const onSubmit = vi.fn().mockResolvedValue({ id: 'u1' });
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [makeCircle({ id: 'c1', name: 'Alpha' })],
				onSubmit
			}
		});

		// Select the circle, enable ALT
		await fireEvent.click(screen.getByText('Alpha'));
		await fireEvent.click(screen.getByTitle('Custom message for Alpha'));

		// Fill the main textarea
		const textareas = screen.getAllByRole('textbox');
		await fireEvent.input(textareas[0], { target: { value: 'Default body' } });

		// Fill the variant textarea
		await fireEvent.input(textareas[1], { target: { value: 'Custom for Alpha' } });

		await fireEvent.click(screen.getByRole('button', { name: /Send/i }));

		const payload = onSubmit.mock.calls[0][0] as Record<string, unknown>;
		expect(payload.body).toBe('Default body');
		expect(payload.circle_bodies).toEqual({ c1: 'Custom for Alpha' });
	});

	it('does NOT include a circle in circle_bodies when ALT is enabled but custom textarea is empty', async () => {
		const onSubmit = vi.fn().mockResolvedValue({ id: 'u1' });
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [makeCircle({ id: 'c1', name: 'Alpha' })],
				onSubmit
			}
		});

		// Select the circle, enable ALT but leave the variant textarea blank
		await fireEvent.click(screen.getByText('Alpha'));
		await fireEvent.click(screen.getByTitle('Custom message for Alpha'));

		const textareas = screen.getAllByRole('textbox');
		await fireEvent.input(textareas[0], { target: { value: 'Default only' } });
		// Intentionally leave textareas[1] empty

		await fireEvent.click(screen.getByRole('button', { name: /Send/i }));

		const payload = onSubmit.mock.calls[0][0] as Record<string, unknown>;
		expect(payload.circle_bodies).toEqual({});
	});

	it('changes main textarea placeholder to show default-message hint when custom is active', async () => {
		render(ComposeBox, {
			props: {
				mode: 'update',
				targetCircles: [makeCircle({ id: 'c1', name: 'Alpha' })],
				onSubmit: vi.fn()
			}
		});

		// Select circle and enable ALT
		await fireEvent.click(screen.getByText('Alpha'));
		await fireEvent.click(screen.getByTitle('Custom message for Alpha'));

		const mainTextarea = screen.getAllByRole('textbox')[0];
		expect(mainTextarea).toHaveAttribute(
			'placeholder',
			'Default message (for circles without a custom message)…'
		);
	});
});
