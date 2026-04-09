export type MemberRole = 'creator' | 'admin' | 'moderator' | 'recipient';

export interface Member {
	id: string;
	role: MemberRole;
	display_handle: string | null;
	joined_at: string;
	circle_id: string | null;
}
