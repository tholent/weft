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

import type { Member } from '$lib/types/member';

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

export function makeMember(overrides: DeepPartial<Member> = {}): Member {
	return {
		id: 'member-1',
		role: 'recipient',
		display_handle: null,
		joined_at: '2026-01-01T00:00:00Z',
		circle_id: 'circle-1',
		notification_channel: 'email',
		has_email: true,
		has_phone: false,
		...overrides
	} as Member;
}
