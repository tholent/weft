import { writable } from 'svelte/store';
import type { Topic } from '$lib/types/topic';
import type { Update } from '$lib/types/update';
import type { Circle } from '$lib/types/circle';
import type { Member } from '$lib/types/member';

export const topic = writable<Topic | null>(null);
export const updates = writable<Update[]>([]);
export const circles = writable<Circle[]>([]);
export const members = writable<Member[]>([]);
