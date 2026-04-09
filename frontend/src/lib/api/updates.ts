import type { Update } from '$lib/types/update';
import { request } from './client';

export function getFeed(topicId: string): Promise<Update[]> {
	return request(`/topics/${topicId}/updates`);
}

export function createUpdate(topicId: string, body: string, circle_ids: string[]): Promise<Update> {
	return request(`/topics/${topicId}/updates`, {
		method: 'POST',
		body: JSON.stringify({ body, circle_ids })
	});
}

export function editUpdate(topicId: string, updateId: string, body: string): Promise<Update> {
	return request(`/topics/${topicId}/updates/${updateId}`, {
		method: 'PATCH',
		body: JSON.stringify({ body })
	});
}

export function deleteUpdate(topicId: string, updateId: string): Promise<void> {
	return request(`/topics/${topicId}/updates/${updateId}`, { method: 'DELETE' });
}
