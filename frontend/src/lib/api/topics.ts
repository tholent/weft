import type { Topic, TopicCreateResponse } from '$lib/types/topic';
import { request } from './client';

export function createTopic(default_title: string, creator_email?: string): Promise<TopicCreateResponse> {
	return request('/topics', {
		method: 'POST',
		body: JSON.stringify({ default_title, creator_email })
	});
}

export function getTopic(topicId: string): Promise<Topic> {
	return request(`/topics/${topicId}`);
}

export function closeTopic(topicId: string): Promise<Topic> {
	return request(`/topics/${topicId}/close`, { method: 'POST' });
}
