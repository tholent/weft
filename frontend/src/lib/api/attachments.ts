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

import type { Attachment } from '$lib/types/attachment';
import { ApiError } from './client';

const API_BASE = '/api';

function getAuthHeaders(): Record<string, string> {
	const token = localStorage.getItem('weft_token');
	return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function uploadAttachment(
	topicId: string,
	updateId: string,
	file: File
): Promise<Attachment> {
	const formData = new FormData();
	formData.append('file', file);

	const res = await fetch(`${API_BASE}/topics/${topicId}/updates/${updateId}/attachments`, {
		method: 'POST',
		headers: getAuthHeaders(),
		body: formData
	});

	if (res.status === 401) {
		localStorage.removeItem('weft_token');
		globalThis.location.href = '/';
		throw new ApiError(401, 'Unauthorized');
	}

	if (!res.ok) {
		const body = await res.json().catch(() => ({ detail: 'Unknown error' }));
		throw new ApiError(res.status, body.detail || 'Upload failed');
	}

	return res.json();
}

export async function listAttachments(topicId: string, updateId: string): Promise<Attachment[]> {
	const res = await fetch(`${API_BASE}/topics/${topicId}/updates/${updateId}/attachments`, {
		headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' }
	});

	if (!res.ok) {
		const body = await res.json().catch(() => ({ detail: 'Unknown error' }));
		throw new ApiError(res.status, body.detail || 'Failed to list attachments');
	}

	return res.json();
}

export function getAttachmentUrl(topicId: string, attachmentId: string): string {
	return `${API_BASE}/topics/${topicId}/attachments/${attachmentId}`;
}
