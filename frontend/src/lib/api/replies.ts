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

import type { Reply, ModResponse, ModResponseScope } from '$lib/types/reply';
import { request } from './client';

export function getReplies(topicId: string, updateId: string): Promise<Reply[]> {
	return request(`/topics/${topicId}/updates/${updateId}/replies`);
}

export function createReply(topicId: string, updateId: string, body: string, wants_to_share = false): Promise<Reply> {
	return request(`/topics/${topicId}/updates/${updateId}/replies`, {
		method: 'POST',
		body: JSON.stringify({ body, wants_to_share })
	});
}

export function relayReply(topicId: string, updateId: string, replyId: string, circle_ids?: string[]): Promise<void> {
	return request(`/topics/${topicId}/updates/${updateId}/replies/${replyId}/relay`, {
		method: 'POST',
		body: JSON.stringify({ circle_ids: circle_ids ?? null })
	});
}

export function dismissReply(topicId: string, updateId: string, replyId: string): Promise<void> {
	return request(`/topics/${topicId}/updates/${updateId}/replies/${replyId}/dismiss`, { method: 'POST' });
}

export function createModResponse(topicId: string, updateId: string, replyId: string, body: string, scope: ModResponseScope): Promise<ModResponse> {
	return request(`/topics/${topicId}/updates/${updateId}/replies/${replyId}/respond`, {
		method: 'POST',
		body: JSON.stringify({ body, scope })
	});
}
