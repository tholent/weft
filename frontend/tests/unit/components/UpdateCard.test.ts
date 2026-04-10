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
import UpdateCard from '$lib/components/UpdateCard.svelte';
import { getAttachmentUrl } from '$lib/api/attachments';
import { makeUpdate, makeCircle, makeAttachment } from '../fixtures';

// The global setup.ts already calls cleanup() in afterEach and wires MSW.
// We only need to restore timers here.
afterEach(() => {
	vi.useRealTimers();
});

// ---------------------------------------------------------------------------
// formatDate branches
// ---------------------------------------------------------------------------

describe('UpdateCard — formatDate', () => {
	it('shows "Today ·" for an update created on the same calendar day', () => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date('2026-04-10T15:00:00Z'));

		const update = makeUpdate({ created_at: '2026-04-10T12:30:00Z' });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		expect(screen.getByText(/Today · /)).toBeInTheDocument();
	});

	it('shows "Yesterday ·" for an update created 1 day ago', () => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date('2026-04-10T15:00:00Z'));

		const update = makeUpdate({ created_at: '2026-04-09T12:30:00Z' });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		expect(screen.getByText(/Yesterday · /)).toBeInTheDocument();
	});

	it('shows a weekday abbreviation for an update created 3 days ago (< 7 days)', () => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date('2026-04-10T15:00:00Z'));

		// 3 days ago = 2026-04-07, which is a Tuesday
		const update = makeUpdate({ created_at: '2026-04-07T12:30:00Z' });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		// The timestamp text should start with a short weekday name (e.g. "Tue · …")
		// We match any 3-letter weekday followed by " · "
		const timestampEl = screen.getByText(/^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) · /);
		expect(timestampEl).toBeInTheDocument();
	});

	it('shows a month/day format for an update created 30 days ago (>= 7 days)', () => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date('2026-04-10T15:00:00Z'));

		// 30 days ago = 2026-03-11
		const update = makeUpdate({ created_at: '2026-03-11T12:30:00Z' });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		// Should not contain Today / Yesterday / a bare weekday prefix
		const timestampEl = document.querySelector('.timestamp') as HTMLElement;
		expect(timestampEl).not.toBeNull();
		expect(timestampEl.textContent).not.toMatch(/^Today/);
		expect(timestampEl.textContent).not.toMatch(/^Yesterday/);
		expect(timestampEl.textContent).not.toMatch(/^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) · /);
		// Should contain " · " with a date portion
		expect(timestampEl.textContent).toMatch(/ · /);
	});
});

// ---------------------------------------------------------------------------
// Deleted state
// ---------------------------------------------------------------------------

describe('UpdateCard — deleted state', () => {
	it('shows [removed] preview text when deleted_at is set', () => {
		const update = makeUpdate({ deleted_at: '2026-01-01T00:00:00Z' });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		expect(screen.getByText('[removed]')).toBeInTheDocument();
	});

	it('applies the "deleted" class to the update-row when deleted_at is set', () => {
		const update = makeUpdate({ deleted_at: '2026-01-01T00:00:00Z' });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		const row = document.querySelector('.update-row');
		expect(row).toHaveClass('deleted');
	});

	it('does not render the attachment grid when deleted_at is set', () => {
		const attachment = makeAttachment({ id: 'att-1' });
		const update = makeUpdate({
			deleted_at: '2026-01-01T00:00:00Z',
			attachments: [attachment]
		});
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		expect(document.querySelector('.attachment-grid')).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// ALT body variants
// ---------------------------------------------------------------------------

describe('UpdateCard — ALT body variants', () => {
	it('renders the ALT badge only on the circle that has a body variant', () => {
		const circles = [
			makeCircle({ id: 'circle-1', name: 'General' }),
			makeCircle({ id: 'circle-2', name: 'VIP' })
		];
		const update = makeUpdate({
			circle_ids: ['circle-1', 'circle-2'],
			body_variants: { 'circle-2': 'alt body for VIP' }
		});
		render(UpdateCard, { props: { update, circles, topicId: 't1' } });

		// The VIP pill should contain ALT
		const altBadges = screen.getAllByText('ALT');
		expect(altBadges).toHaveLength(1);

		// The VIP pill's parent span should have pill-variant class
		const altBadge = altBadges[0];
		const pill = altBadge.closest('.pill');
		expect(pill).toHaveClass('pill-variant');
	});

	it('does not render ALT on the circle without a body variant', () => {
		const circles = [
			makeCircle({ id: 'circle-1', name: 'General' }),
			makeCircle({ id: 'circle-2', name: 'VIP' })
		];
		const update = makeUpdate({
			circle_ids: ['circle-1', 'circle-2'],
			body_variants: { 'circle-2': 'alt body for VIP' }
		});
		render(UpdateCard, { props: { update, circles, topicId: 't1' } });

		// The General pill should NOT have pill-variant
		const allPills = document.querySelectorAll('.pill');
		const generalPill = Array.from(allPills).find(
			(p) => p.textContent?.includes('General') && !p.textContent?.includes('ALT')
		);
		expect(generalPill).toBeDefined();
		expect(generalPill).not.toHaveClass('pill-variant');
	});
});

// ---------------------------------------------------------------------------
// Reply count badges
// ---------------------------------------------------------------------------

describe('UpdateCard — reply count badge', () => {
	it('renders "1 reply" when reply_count is 1', () => {
		const update = makeUpdate({ reply_count: 1 });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		expect(screen.getByText('1 reply')).toBeInTheDocument();
	});

	it('renders "5 replies" when reply_count is 5', () => {
		const update = makeUpdate({ reply_count: 5 });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		expect(screen.getByText('5 replies')).toBeInTheDocument();
	});

	it('does not render a reply badge when reply_count is 0', () => {
		const update = makeUpdate({ reply_count: 0 });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		expect(screen.queryByText(/repl(y|ies)/)).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Pending reply badges
// ---------------------------------------------------------------------------

describe('UpdateCard — pending reply badge', () => {
	it('renders "2 pending" when pending_reply_count is 2', () => {
		const update = makeUpdate({ pending_reply_count: 2 });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		expect(screen.getByText('2 pending')).toBeInTheDocument();
	});

	it('does not render a pending badge when pending_reply_count is 0', () => {
		const update = makeUpdate({ pending_reply_count: 0 });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		expect(screen.queryByText(/pending/)).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Attachment grid
// ---------------------------------------------------------------------------

describe('UpdateCard — attachment grid', () => {
	it('renders exactly 2 thumbnail buttons for an update with 2 attachments', () => {
		const att1 = makeAttachment({ id: 'att-1', filename: 'photo1.jpg' });
		const att2 = makeAttachment({ id: 'att-2', filename: 'photo2.jpg' });
		const update = makeUpdate({ attachments: [att1, att2] });

		render(UpdateCard, { props: { update, circles: [], topicId: 'topic-abc' } });

		const thumbBtns = document.querySelectorAll('.thumb-btn');
		expect(thumbBtns).toHaveLength(2);
	});

	it('thumbnail img src includes the attachment ID', () => {
		const att = makeAttachment({ id: 'att-unique', filename: 'image.png' });
		const update = makeUpdate({ attachments: [att] });

		render(UpdateCard, { props: { update, circles: [], topicId: 'topic-xyz' } });

		const img = document.querySelector('.thumb') as HTMLImageElement;
		expect(img).not.toBeNull();
		expect(img.src).toContain('att-unique');
	});

	it('thumbnail img src matches getAttachmentUrl output', () => {
		const att = makeAttachment({ id: 'att-check', filename: 'check.png' });
		const update = makeUpdate({ attachments: [att] });
		const topicId = 'topic-check';

		render(UpdateCard, { props: { update, circles: [], topicId } });

		const expectedSrc = getAttachmentUrl(topicId, att.id);
		const img = document.querySelector('.thumb') as HTMLImageElement;
		// jsdom resolves relative URLs against the base, so we compare the pathname
		expect(img.getAttribute('src')).toBe(expectedSrc);
	});
});

// ---------------------------------------------------------------------------
// Lightbox state transitions
// ---------------------------------------------------------------------------

describe('UpdateCard — lightbox', () => {
	it('does not show a lightbox overlay initially', () => {
		const att = makeAttachment({ id: 'att-lb', filename: 'lb.png' });
		const update = makeUpdate({ attachments: [att] });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		expect(screen.queryByAltText('Full size')).toBeNull();
	});

	it('opens the lightbox when a thumbnail button is clicked', async () => {
		const att = makeAttachment({ id: 'att-lb2', filename: 'lb2.png' });
		const update = makeUpdate({ attachments: [att] });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		const thumbBtn = document.querySelector('.thumb-btn') as HTMLButtonElement;
		await fireEvent.click(thumbBtn);

		const lightboxImg = screen.getByAltText('Full size') as HTMLImageElement;
		expect(lightboxImg).toBeInTheDocument();
		expect(lightboxImg.getAttribute('src')).toContain('att-lb2');
	});

	it('closes the lightbox when the overlay is clicked', async () => {
		const att = makeAttachment({ id: 'att-lb3', filename: 'lb3.png' });
		const update = makeUpdate({ attachments: [att] });
		render(UpdateCard, { props: { update, circles: [], topicId: 't1' } });

		// Open lightbox
		const thumbBtn = document.querySelector('.thumb-btn') as HTMLButtonElement;
		await fireEvent.click(thumbBtn);
		expect(screen.getByAltText('Full size')).toBeInTheDocument();

		// Close lightbox by clicking overlay
		const overlay = document.querySelector('.lightbox-overlay') as HTMLElement;
		await fireEvent.click(overlay);

		expect(screen.queryByAltText('Full size')).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// stopPropagation invariant on thumbnail click
// ---------------------------------------------------------------------------

describe('UpdateCard — stopPropagation on thumbnail click', () => {
	it('does NOT call the row onClick when a thumbnail button is clicked', async () => {
		const att = makeAttachment({ id: 'att-sp', filename: 'sp.png' });
		const update = makeUpdate({ attachments: [att] });
		const onClick = vi.fn();

		render(UpdateCard, { props: { update, circles: [], topicId: 't1', onClick } });

		const thumbBtn = document.querySelector('.thumb-btn') as HTMLButtonElement;
		await fireEvent.click(thumbBtn);

		expect(onClick).not.toHaveBeenCalled();
	});

	it('DOES call the row onClick when the row body (preview text) is clicked', async () => {
		const update = makeUpdate({ body: 'Clickable update text' });
		const onClick = vi.fn();

		render(UpdateCard, { props: { update, circles: [], topicId: 't1', onClick } });

		const preview = screen.getByText('Clickable update text');
		await fireEvent.click(preview);

		expect(onClick).toHaveBeenCalledOnce();
	});
});
