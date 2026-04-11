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

import { describe, it, expect, vi, beforeEach, afterEach, type MockInstance } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/msw-server';
import { exportTopic, downloadTopicExport } from '$lib/api/export';
import type { TopicExport } from '$lib/types/export';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeTopicExport(overrides: Partial<TopicExport> = {}): TopicExport {
	return {
		topic: {
			title: 'Test Topic',
			status: 'open',
			created_at: '2026-01-01T00:00:00Z',
			closed_at: null
		},
		circles: [],
		updates: [],
		relays: [],
		exported_at: '2026-01-10T00:00:00Z',
		...overrides
	};
}

// ---------------------------------------------------------------------------
// exportTopic
// ---------------------------------------------------------------------------

describe('exportTopic', () => {
	it('sends GET to /api/topics/:topicId/export and returns TopicExport', async () => {
		const fakeExport = makeTopicExport({ exported_at: '2026-04-10T00:00:00Z' });

		server.use(
			http.get('http://localhost/api/topics/:topicId/export', () => {
				return HttpResponse.json(fakeExport);
			})
		);

		const result = await exportTopic('topic-99');

		expect(result.exported_at).toBe('2026-04-10T00:00:00Z');
		expect(result.topic.title).toBe('Test Topic');
	});

	it('requests the correct topic id in the URL path', async () => {
		let capturedUrl: string | undefined;
		const fakeExport = makeTopicExport();

		server.use(
			http.get('http://localhost/api/topics/:topicId/export', ({ request }) => {
				capturedUrl = request.url;
				return HttpResponse.json(fakeExport);
			})
		);

		await exportTopic('topic-abc');

		expect(capturedUrl).toContain('/api/topics/topic-abc/export');
	});
});

// ---------------------------------------------------------------------------
// downloadTopicExport
// ---------------------------------------------------------------------------

describe('downloadTopicExport', () => {
	// vi.spyOn returns a tightly-typed MockInstance bound to the spied method
	// signature; using `MockInstance` (any-args) avoids variance issues with
	// the strict overloaded signatures of createElement/appendChild.
	let createObjUrlSpy: MockInstance;
	let revokeObjUrlSpy: MockInstance;
	let createElementSpy: MockInstance;
	let appendChildSpy: MockInstance;
	let fakeAnchor: HTMLAnchorElement;
	let clickSpy: MockInstance;
	let removeSpy: MockInstance;

	beforeEach(() => {
		// jsdom does not implement these — define stubs so vi.spyOn has something to attach to.
		if (typeof URL.createObjectURL !== 'function') {
			Object.defineProperty(URL, 'createObjectURL', {
				value: () => '',
				writable: true,
				configurable: true
			});
		}
		if (typeof URL.revokeObjectURL !== 'function') {
			Object.defineProperty(URL, 'revokeObjectURL', {
				value: () => {},
				writable: true,
				configurable: true
			});
		}

		// Stub URL object methods
		createObjUrlSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:fake-url');
		revokeObjUrlSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

		// Create a real anchor before installing spy, so we have a genuine anchor to return
		const originalCreateElement = document.createElement.bind(document);
		fakeAnchor = originalCreateElement('a');
		clickSpy = vi.spyOn(fakeAnchor, 'click').mockImplementation(() => {});
		removeSpy = vi.spyOn(fakeAnchor, 'remove').mockImplementation(() => {});

		// Spy on createElement to return the fake anchor when 'a' is requested.
		// Cast via unknown to satisfy TypeScript's overloaded createElement signature.
		createElementSpy = vi.spyOn(document, 'createElement').mockImplementation(((tag: string) => {
			if (tag === 'a') return fakeAnchor;
			// Fall through to real implementation for other tags
			return originalCreateElement(tag);
		}) as typeof document.createElement);

		// Spy on document.body.appendChild so click/cleanup can be observed
		appendChildSpy = vi
			.spyOn(document.body, 'appendChild')
			.mockImplementation((node) => node as Node);
	});

	afterEach(() => {
		createObjUrlSpy.mockRestore();
		revokeObjUrlSpy.mockRestore();
		createElementSpy.mockRestore();
		appendChildSpy.mockRestore();
		clickSpy.mockRestore();
		removeSpy.mockRestore();
	});

	it('creates an object URL, sets anchor href and download, clicks, removes, and revokes', async () => {
		const fakeExport = makeTopicExport();

		server.use(
			http.get('http://localhost/api/topics/t1/export', () => {
				return HttpResponse.json(fakeExport);
			})
		);

		await downloadTopicExport('t1');

		// createObjectURL called with a Blob
		expect(createObjUrlSpy).toHaveBeenCalledOnce();
		const blobArg = createObjUrlSpy.mock.calls[0][0];
		expect(blobArg).toBeInstanceOf(Blob);

		// Anchor href set to the object URL
		expect(fakeAnchor.href).toContain('blob:fake-url');

		// download filename includes the topic id
		expect(fakeAnchor.download).toBe('weft-export-t1.json');

		// anchor appended to body, clicked, then removed
		expect(appendChildSpy).toHaveBeenCalledWith(fakeAnchor);
		expect(clickSpy).toHaveBeenCalledOnce();
		expect(removeSpy).toHaveBeenCalledOnce();

		// object URL revoked after click
		expect(revokeObjUrlSpy).toHaveBeenCalledWith('blob:fake-url');
	});

	it('sets correct download filename for different topic ids', async () => {
		const fakeExport = makeTopicExport();

		server.use(
			http.get('http://localhost/api/topics/my-topic-123/export', () => {
				return HttpResponse.json(fakeExport);
			})
		);

		await downloadTopicExport('my-topic-123');

		expect(fakeAnchor.download).toBe('weft-export-my-topic-123.json');
	});

	it('blob contains JSON-serialised export data', async () => {
		const fakeExport = makeTopicExport({ exported_at: '2026-04-10T12:00:00Z' });

		server.use(
			http.get('http://localhost/api/topics/t2/export', () => {
				return HttpResponse.json(fakeExport);
			})
		);

		// jsdom's Blob does not expose its contents back via .text() / .arrayBuffer()
		// reliably, so wrap the global Blob constructor to capture the parts and
		// type at construction time.
		const OriginalBlob = globalThis.Blob;
		const blobCalls: { parts: BlobPart[]; type: string | undefined }[] = [];
		const BlobSpy = vi.fn((parts: BlobPart[], options?: BlobPropertyBag) => {
			blobCalls.push({ parts, type: options?.type });
			return new OriginalBlob(parts, options);
		}) as unknown as typeof Blob;
		globalThis.Blob = BlobSpy;

		try {
			await downloadTopicExport('t2');
		} finally {
			globalThis.Blob = OriginalBlob;
		}

		// MSW's HttpResponse.json constructs its own Blob for the response body,
		// so multiple Blob() calls may be observed. The download blob is the
		// one tagged 'application/json' from user code.
		const downloadBlob = blobCalls.find((c) => c.type === 'application/json');
		expect(downloadBlob).toBeDefined();

		const text = downloadBlob!.parts[0] as string;
		const parsed = JSON.parse(text) as TopicExport;
		expect(parsed.exported_at).toBe('2026-04-10T12:00:00Z');
	});

	it('operations occur in correct order: createObjectURL → appendChild → click → remove → revokeObjectURL', async () => {
		const callOrder: string[] = [];

		createObjUrlSpy.mockImplementation(() => {
			callOrder.push('createObjectURL');
			return 'blob:ordered-url';
		});
		appendChildSpy.mockImplementation((node) => {
			callOrder.push('appendChild');
			return node as Node;
		});
		clickSpy.mockImplementation(() => {
			callOrder.push('click');
		});
		removeSpy.mockImplementation(() => {
			callOrder.push('remove');
		});
		revokeObjUrlSpy.mockImplementation(() => {
			callOrder.push('revokeObjectURL');
		});

		const fakeExport = makeTopicExport();
		server.use(
			http.get('http://localhost/api/topics/t3/export', () => {
				return HttpResponse.json(fakeExport);
			})
		);

		await downloadTopicExport('t3');

		expect(callOrder).toEqual([
			'createObjectURL',
			'appendChild',
			'click',
			'remove',
			'revokeObjectURL'
		]);
	});
});
