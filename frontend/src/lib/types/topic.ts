export type TopicStatus = 'active' | 'closed' | 'archived';

export interface Topic {
	id: string;
	default_title: string;
	status: TopicStatus;
	created_at: string;
	closed_at: string | null;
	scoped_title: string | null;
}

export interface TopicCreateResponse {
	topic: Topic;
	token: string;
	magic_link: string;
}
