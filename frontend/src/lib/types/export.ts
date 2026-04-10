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

export interface ExportedAttachment {
	filename: string;
	content_type: string;
	storage_key: string;
}

export interface ExportedModResponse {
	body: string;
	author: string | null;
	scope: string;
	created_at: string;
}

export interface ExportedReply {
	body: string;
	author: string | null;
	wants_to_share: boolean;
	relay_status: string;
	created_at: string;
	mod_responses: ExportedModResponse[];
}

export interface ExportedUpdate {
	body: string;
	author: string | null;
	circles: string[];
	attachments: ExportedAttachment[];
	replies: ExportedReply[];
	created_at: string;
	edited_at: string | null;
}

export interface ExportedCircle {
	name: string;
	scoped_title: string | null;
}

export interface ExportedRelay {
	reply_id: string;
	relayed_by: string | null;
	circle: string | null;
	relayed_at: string;
}

export interface TopicExport {
	topic: {
		title: string;
		status: string;
		created_at: string;
		closed_at: string | null;
	};
	circles: ExportedCircle[];
	updates: ExportedUpdate[];
	relays: ExportedRelay[];
	exported_at: string;
}
