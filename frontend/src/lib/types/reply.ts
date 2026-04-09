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

export type RelayStatus = 'pending' | 'relayed' | 'dismissed';
export type ModResponseScope = 'sender_only' | 'sender_circle' | 'all_circles';

export interface ModResponse {
	id: string;
	body: string;
	author_handle: string | null;
	scope: ModResponseScope;
	created_at: string;
}

export interface Reply {
	id: string;
	body: string;
	author_member_id: string;
	author_handle: string | null;
	wants_to_share: boolean;
	relay_status: RelayStatus;
	created_at: string;
	mod_responses: ModResponse[];
}
