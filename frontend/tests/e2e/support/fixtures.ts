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

import { test as base, expect } from '@playwright/test';
import { SeedClient } from '../fixtures/seed-client';
import type { SeedTopicSpec } from '../fixtures/seed-client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SeededTopic {
	topicId: string;
	ownerBearer: string;
	ownerMagic: string;
	adminMagic: Record<string, string>;
	moderatorMagic: Record<string, string>;
	recipientMagic: Record<string, string>;
	circleIds: Record<string, string>;
}

interface Fixtures {
	seedClient: SeedClient;
	seededTopic: SeededTopic;
}

// ---------------------------------------------------------------------------
// Default seed spec — one circle "Family" with two recipients, one admin,
// one moderator, plus the owner.
// ---------------------------------------------------------------------------

const DEFAULT_SEED_SPEC: SeedTopicSpec = {
	title: 'E2E Seed Topic',
	owner_email: 'owner@example.com',
	owner_name: 'Seed Owner',
	circles: [
		{
			name: 'Family',
			members: [
				{ email: 'alice@example.com', role: 'recipient', name: 'Alice' },
				{ email: 'bob@example.com', role: 'recipient', name: 'Bob' },
				{ email: 'admin@example.com', role: 'admin', name: 'Admin User' },
				{ email: 'mod@example.com', role: 'moderator', name: 'Mod User' }
			]
		}
	]
};

// ---------------------------------------------------------------------------
// Extended test object
// ---------------------------------------------------------------------------

export const test = base.extend<Fixtures>({
	seedClient: async ({ request }, use) => {
		await use(new SeedClient(request));
	},

	seededTopic: async ({ seedClient }, use) => {
		await seedClient.reset();
		const data = await seedClient.seedTopic(DEFAULT_SEED_SPEC);

		const topic: SeededTopic = {
			topicId: data.topic_id,
			ownerBearer: data.owner_token,
			ownerMagic: data.magic_links.owner,
			adminMagic: data.magic_links.admins,
			moderatorMagic: data.magic_links.moderators,
			recipientMagic: data.magic_links.recipients,
			circleIds: data.circle_ids
		};

		await use(topic);

		// Optional teardown — reset the DB after the test so the next test
		// always starts from a clean state.
		await seedClient.reset();
	}
});

export { expect };
