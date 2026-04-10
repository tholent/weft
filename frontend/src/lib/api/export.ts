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

import type { TopicExport } from '$lib/types/export';
import { request } from './client';

/**
 * Fetch the full topic export as a structured object.
 * Owner only.
 */
export function exportTopic(topicId: string): Promise<TopicExport> {
	return request(`/topics/${topicId}/export`);
}

/**
 * Trigger a browser download of the topic export as a JSON file.
 * This fetches the export and creates a temporary anchor element to download it.
 */
export async function downloadTopicExport(topicId: string): Promise<void> {
	const data = await exportTopic(topicId);
	const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = `weft-export-${topicId}.json`;
	document.body.appendChild(a);
	a.click();
	a.remove();
	URL.revokeObjectURL(url);
}
