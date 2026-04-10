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

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

export function makeUpdate(overrides: DeepPartial<Update> = {}): Update {
	return {
		id: 'update-1',
		body: 'Test update body',
		author_member_id: 'member-1',
		author_handle: null,
		circle_ids: ['circle-1'],
		body_variants: {},
		created_at: '2026-01-01T00:00:00Z',
		edited_at: null,
		deleted_at: null,
		reply_count: 0,
		pending_reply_count: 0,
		attachments: [],
		...overrides
	} as Update;
}
