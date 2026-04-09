export type RelayStatus = 'pending' | 'relayed' | 'dismissed';
export type ModResponseScope = 'sender_only' | 'sender_circle' | 'all_circles';

export interface ModResponse {
	id: string;
	body: string;
	author_handle: string | null;
	scope: ModResponseScope;
	created_at: string;
}

export interface Reply {
	id: string;
	body: string;
	author_member_id: string;
	author_handle: string | null;
	wants_to_share: boolean;
	relay_status: RelayStatus;
	created_at: string;
	mod_responses: ModResponse[];
}
