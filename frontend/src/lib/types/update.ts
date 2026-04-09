export interface Update {
	id: string;
	body: string;
	author_member_id: string;
	author_handle: string | null;
	circle_ids: string[];
	created_at: string;
	edited_at: string | null;
	deleted_at: string | null;
	reply_count: number;
}
