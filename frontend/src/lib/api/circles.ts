import type { Circle } from '$lib/types/circle';
import { request } from './client';

export function listCircles(topicId: string): Promise<Circle[]> {
	return request(`/topics/${topicId}/circles`);
}

export function createCircle(topicId: string, name: string, scoped_title?: string): Promise<Circle> {
	return request(`/topics/${topicId}/circles`, {
		method: 'POST',
		body: JSON.stringify({ name, scoped_title })
	});
}

export function renameCircle(topicId: string, circleId: string, name?: string, scoped_title?: string): Promise<Circle> {
	return request(`/topics/${topicId}/circles/${circleId}`, {
		method: 'PATCH',
		body: JSON.stringify({ name, scoped_title })
	});
}

export function deleteCircle(topicId: string, circleId: string): Promise<void> {
	return request(`/topics/${topicId}/circles/${circleId}`, { method: 'DELETE' });
}
