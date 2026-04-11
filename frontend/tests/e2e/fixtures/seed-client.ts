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

import type { APIRequestContext } from '@playwright/test';

// ---------------------------------------------------------------------------
// Request/response shape types — mirror the backend Pydantic models
// ---------------------------------------------------------------------------

export interface SeedMemberSpec {
	email: string;
	role: 'owner' | 'admin' | 'moderator' | 'recipient';
	name?: string;
}

export interface SeedCircleSpec {
	name: string;
	members?: SeedMemberSpec[];
}

export interface SeedUpdateSpec {
	body: string;
	circle_names: string[];
	author_email: string;
}

export interface SeedReplySpec {
	update_index: number;
	author_email: string;
	body: string;
}

export interface SeedTopicSpec {
	title?: string;
	owner_email?: string;
	owner_name?: string;
	circles?: SeedCircleSpec[];
	updates?: SeedUpdateSpec[];
	replies?: SeedReplySpec[];
}

export interface SeedMagicLinks {
	owner: string;
	admins: Record<string, string>;
	moderators: Record<string, string>;
	recipients: Record<string, string>;
}

export interface SeedTopicResponse {
	topic_id: string;
	owner_token: string;
	admin_tokens: Record<string, string>;
	moderator_tokens: Record<string, string>;
	recipient_tokens: Record<string, string>;
	circle_ids: Record<string, string>;
	magic_links: SeedMagicLinks;
}

// ---------------------------------------------------------------------------
// SeedClient — typed wrapper around the backend /test/seed endpoints
// ---------------------------------------------------------------------------

export class SeedClient {
	private readonly request: APIRequestContext;
	private readonly baseURL: string;

	constructor(request: APIRequestContext, baseURL: string = 'http://127.0.0.1:8001') {
		this.request = request;
		this.baseURL = baseURL;
	}

	/** Truncate all application tables via POST /test/seed/reset. */
	async reset(): Promise<void> {
		const response = await this.request.post(`${this.baseURL}/test/seed/reset`);
		if (!response.ok()) {
			throw new Error(`seed reset failed: ${response.status()} ${await response.text()}`);
		}
	}

	/** Create a topic from the given spec and return typed seed data. */
	async seedTopic(spec: SeedTopicSpec): Promise<SeedTopicResponse> {
		const response = await this.request.post(`${this.baseURL}/test/seed/topic`, {
			data: spec
		});
		if (!response.ok()) {
			throw new Error(`seed topic failed: ${response.status()} ${await response.text()}`);
		}
		return (await response.json()) as SeedTopicResponse;
	}
}
