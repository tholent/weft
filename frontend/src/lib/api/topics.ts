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

import type { Topic, TopicCreateResponse } from '$lib/types/topic';
import { request } from './client';

export function createTopic(default_title: string, creator_email?: string): Promise<TopicCreateResponse> {
	return request('/topics', {
		method: 'POST',
		body: JSON.stringify({ default_title, creator_email })
	});
}

export function getTopic(topicId: string): Promise<Topic> {
	return request(`/topics/${topicId}`);
}

export function closeTopic(topicId: string): Promise<Topic> {
	return request(`/topics/${topicId}/close`, { method: 'POST' });
}
