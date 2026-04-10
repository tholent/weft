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
import ExportButton from '$lib/components/ExportButton.svelte';

vi.mock('$lib/api/export', () => ({
	downloadTopicExport: vi.fn()
}));

import { downloadTopicExport } from '$lib/api/export';

// ---------------------------------------------------------------------------
// Click triggers download
// ---------------------------------------------------------------------------

describe('ExportButton — click triggers download', () => {
	it('calls downloadTopicExport with the topicId when the button is clicked', async () => {
		const mockFn = vi.mocked(downloadTopicExport);
		mockFn.mockResolvedValue(undefined);

		render(ExportButton, { props: { topicId: 'topic-abc' } });

		const button = screen.getByRole('button', { name: /export topic data/i });
		await fireEvent.click(button);

		expect(mockFn).toHaveBeenCalledOnce();
		expect(mockFn).toHaveBeenCalledWith('topic-abc');
	});
});

// ---------------------------------------------------------------------------
// Disabled in-flight state
// ---------------------------------------------------------------------------

describe('ExportButton — disabled in-flight state', () => {
	it('disables the button and shows "Exporting..." text while the download is in flight', async () => {
		const mockFn = vi.mocked(downloadTopicExport);
		// A promise that never resolves simulates an in-flight request
		mockFn.mockReturnValue(new Promise(() => {}));

		render(ExportButton, { props: { topicId: 'topic-xyz' } });

		const button = screen.getByRole('button', { name: /export topic data/i });
		await fireEvent.click(button);

		// After click the button should be disabled and show loading text
		const loadingButton = screen.getByRole('button', { name: /exporting/i });
		expect(loadingButton).toBeDisabled();
	});
});

// ---------------------------------------------------------------------------
// Re-enabled after completion
// ---------------------------------------------------------------------------

describe('ExportButton — re-enabled after completion', () => {
	it('re-enables the button after the download resolves successfully', async () => {
		const mockFn = vi.mocked(downloadTopicExport);

		let resolve!: () => void;
		const pendingPromise = new Promise<void>((res) => {
			resolve = res;
		});
		mockFn.mockReturnValue(pendingPromise);

		render(ExportButton, { props: { topicId: 'topic-def' } });

		const button = screen.getByRole('button', { name: /export topic data/i });
		await fireEvent.click(button);

		// Should be disabled while in flight
		expect(screen.getByRole('button', { name: /exporting/i })).toBeDisabled();

		// Resolve the promise
		resolve();
		await pendingPromise;

		// After resolution the button should be re-enabled with the original text.
		// The async state update needs a tick to flush, so wait for it.
		await waitFor(() => {
			const reenabledButton = screen.getByRole('button', { name: /export topic data/i });
			expect(reenabledButton).not.toBeDisabled();
		});
	});

	it('shows an error message when downloadTopicExport throws', async () => {
		const mockFn = vi.mocked(downloadTopicExport);
		mockFn.mockRejectedValue(new Error('Network error'));

		render(ExportButton, { props: { topicId: 'topic-fail' } });

		const button = screen.getByRole('button', { name: /export topic data/i });
		await fireEvent.click(button);

		// After rejection the error text should appear
		const errorText = await screen.findByText(/export failed/i);
		expect(errorText).toBeInTheDocument();

		// Button should also be re-enabled
		expect(screen.getByRole('button', { name: /export topic data/i })).not.toBeDisabled();
	});
});
