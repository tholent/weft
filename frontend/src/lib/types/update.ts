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

import type { Attachment } from './attachment';

export interface Update {
	id: string;
	body: string;
	author_member_id: string;
	author_handle: string | null;
	circle_ids: string[];
	body_variants: Record<string, string>;
	created_at: string;
	edited_at: string | null;
	deleted_at: string | null;
	reply_count: number;
	pending_reply_count: number;
	attachments: Attachment[];
}
