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

import type { Update } from '$lib/types/update';
import { request } from './client';

export async function getFeed(topicId: string): Promise<Update[]> {
	const data = await request<{ items: Update[] }>(`/topics/${topicId}/updates`);
	return data.items;
}

export function createUpdate(
	topicId: string,
	body: string,
	circle_ids: string[],
	circle_bodies: Record<string, string> = {}
): Promise<Update> {
	return request(`/topics/${topicId}/updates`, {
		method: 'POST',
		body: JSON.stringify({ body, circle_ids, circle_bodies })
	});
}

export function editUpdate(
	topicId: string,
	updateId: string,
	body: string,
	circle_bodies: Record<string, string> = {}
): Promise<Update> {
	return request(`/topics/${topicId}/updates/${updateId}`, {
		method: 'PATCH',
		body: JSON.stringify({ body, circle_bodies })
	});
}

export function deleteUpdate(topicId: string, updateId: string): Promise<void> {
	return request(`/topics/${topicId}/updates/${updateId}`, { method: 'DELETE' });
}
