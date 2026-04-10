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

import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { topic, updates, circles, members } from '$lib/stores/topic';
import { makeTopic, makeUpdate, makeCircle, makeMember } from '../fixtures';

beforeEach(() => {
	topic.set(null);
	updates.set([]);
	circles.set([]);
	members.set([]);
});

describe('topic store', () => {
	it('starts as null', () => {
		expect(get(topic)).toBeNull();
	});

	it('stores and retrieves a topic', () => {
		const t = makeTopic({ id: 'topic-abc', default_title: 'My Topic' });
		topic.set(t);
		expect(get(topic)).toEqual(t);
	});

	it('resets to null', () => {
		topic.set(makeTopic());
		topic.set(null);
		expect(get(topic)).toBeNull();
	});
});

describe('updates store', () => {
	it('starts as an empty array', () => {
		expect(get(updates)).toEqual([]);
	});

	it('stores and retrieves a list of updates', () => {
		const u1 = makeUpdate({ id: 'update-1', body: 'First update' });
		const u2 = makeUpdate({ id: 'update-2', body: 'Second update' });
		updates.set([u1, u2]);
		expect(get(updates)).toEqual([u1, u2]);
	});

	it('resets to an empty array', () => {
		updates.set([makeUpdate()]);
		updates.set([]);
		expect(get(updates)).toEqual([]);
	});
});

describe('circles store', () => {
	it('starts as an empty array', () => {
		expect(get(circles)).toEqual([]);
	});

	it('stores and retrieves a list of circles', () => {
		const c1 = makeCircle({ id: 'circle-1', name: 'Alpha' });
		const c2 = makeCircle({ id: 'circle-2', name: 'Beta' });
		circles.set([c1, c2]);
		expect(get(circles)).toEqual([c1, c2]);
	});

	it('resets to an empty array', () => {
		circles.set([makeCircle()]);
		circles.set([]);
		expect(get(circles)).toEqual([]);
	});
});

describe('members store', () => {
	it('starts as an empty array', () => {
		expect(get(members)).toEqual([]);
	});

	it('stores and retrieves a list of members', () => {
		const m1 = makeMember({ id: 'member-1', role: 'admin' });
		const m2 = makeMember({ id: 'member-2', role: 'recipient' });
		members.set([m1, m2]);
		expect(get(members)).toEqual([m1, m2]);
	});

	it('resets to an empty array', () => {
		members.set([makeMember()]);
		members.set([]);
		expect(get(members)).toEqual([]);
	});
});
