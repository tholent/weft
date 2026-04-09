export type TransferStatus = 'pending' | 'confirmed' | 'denied' | 'expired';

export interface CreatorTransfer {
	id: string;
	status: TransferStatus;
	deadline: string;
	created_at: string;
}
