import type { CreatorTransfer } from '$lib/types/transfer';
import { request } from './client';

export function requestTransfer(topicId: string): Promise<CreatorTransfer> {
	return request(`/topics/${topicId}/transfer`, { method: 'POST' });
}

export function getTransferStatus(topicId: string): Promise<CreatorTransfer | null> {
	return request(`/topics/${topicId}/transfer`);
}

export function cancelTransfer(topicId: string): Promise<void> {
	return request(`/topics/${topicId}/transfer/cancel`, { method: 'POST' });
}
