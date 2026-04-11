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

import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/msw-server';
import {
	requestTransfer,
	getTransferStatus,
	cancelTransfer,
	directTransfer
} from '$lib/api/transfer';
import type { CreatorTransfer } from '$lib/types/transfer';

function makeTransfer(overrides: Partial<CreatorTransfer> = {}): CreatorTransfer {
	return {
		id: 'transfer-1',
		status: 'pending',
		deadline: '2026-04-11T00:00:00Z',
		created_at: '2026-04-10T00:00:00Z',
		...overrides
	};
}

// ---------------------------------------------------------------------------
// requestTransfer
// ---------------------------------------------------------------------------

describe('requestTransfer', () => {
	it('sends POST to /api/topics/:id/transfer and returns the transfer', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;
		const fakeTransfer = makeTransfer({ id: 'transfer-10', status: 'pending' });

		server.use(
			http.post('http://localhost/api/topics/:id/transfer', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return HttpResponse.json(fakeTransfer);
			})
		);

		const result = await requestTransfer('topic-42');

		expect(capturedMethod).toBe('POST');
		expect(capturedUrl).toContain('/api/topics/topic-42/transfer');
		expect(result.id).toBe('transfer-10');
		expect(result.status).toBe('pending');
	});
});

// ---------------------------------------------------------------------------
// getTransferStatus
// ---------------------------------------------------------------------------

describe('getTransferStatus', () => {
	it('sends GET to /api/topics/:id/transfer and returns the transfer', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;
		const fakeTransfer = makeTransfer({ id: 'transfer-20', status: 'pending' });

		server.use(
			http.get('http://localhost/api/topics/:id/transfer', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return HttpResponse.json(fakeTransfer);
			})
		);

		const result = await getTransferStatus('topic-77');

		expect(capturedMethod).toBe('GET');
		expect(capturedUrl).toContain('/api/topics/topic-77/transfer');
		expect(result).not.toBeNull();
		expect((result as CreatorTransfer).id).toBe('transfer-20');
	});

	it('returns null when the server responds with null', async () => {
		server.use(
			http.get('http://localhost/api/topics/:id/transfer', () => {
				return HttpResponse.json(null);
			})
		);

		const result = await getTransferStatus('topic-00');

		expect(result).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// cancelTransfer
// ---------------------------------------------------------------------------

describe('cancelTransfer', () => {
	it('sends POST to /api/topics/:id/transfer/cancel', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;

		server.use(
			http.post('http://localhost/api/topics/:id/transfer/cancel', ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				return new HttpResponse(null, { status: 204 });
			})
		);

		await cancelTransfer('topic-55');

		expect(capturedMethod).toBe('POST');
		expect(capturedUrl).toContain('/api/topics/topic-55/transfer/cancel');
	});
});

// ---------------------------------------------------------------------------
// directTransfer
// ---------------------------------------------------------------------------

describe('directTransfer', () => {
	it('sends POST to /api/topics/:id/transfer/direct with target_member_id in body', async () => {
		let capturedMethod: string | undefined;
		let capturedUrl: string | undefined;
		let capturedBody: unknown;

		server.use(
			http.post('http://localhost/api/topics/:id/transfer/direct', async ({ request }) => {
				capturedMethod = request.method;
				capturedUrl = request.url;
				capturedBody = await request.json();
				return new HttpResponse(null, { status: 204 });
			})
		);

		await directTransfer('topic-33', 'member-99');

		expect(capturedMethod).toBe('POST');
		expect(capturedUrl).toContain('/api/topics/topic-33/transfer/direct');
		expect(capturedBody).toEqual({ target_member_id: 'member-99' });
	});
});
