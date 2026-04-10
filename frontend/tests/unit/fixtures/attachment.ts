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

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

export function makeAttachment(overrides: DeepPartial<Attachment> = {}): Attachment {
	return {
		id: 'attachment-1',
		update_id: 'update-1',
		topic_id: 'topic-1',
		filename: 'sample.png',
		content_type: 'image/png',
		size_bytes: 1024,
		created_at: '2026-01-01T00:00:00Z',
		...overrides
	} as Attachment;
}
