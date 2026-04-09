<script lang="ts">
	import { onMount } from 'svelte';
	import { session, isCreator, isAdmin } from '$lib/stores/session';
	import { requestTransfer, getTransferStatus, cancelTransfer } from '$lib/api/transfer';
	import type { CreatorTransfer } from '$lib/types/transfer';

	let transfer: CreatorTransfer | null = null;
	let timeLeft = '';

	onMount(async () => {
		if (!$session.topicId) return;
		try {
			transfer = await getTransferStatus($session.topicId);
		} catch {
			// no pending transfer
		}
	});

	function updateCountdown() {
		if (!transfer?.deadline) return;
		const diff = new Date(transfer.deadline).getTime() - Date.now();
		if (diff <= 0) {
			timeLeft = 'Expired';
		} else {
			const h = Math.floor(diff / 3600000);
			const m = Math.floor((diff % 3600000) / 60000);
			timeLeft = `${h}h ${m}m`;
		}
	}

	$: if (transfer) {
		updateCountdown();
	}

	async function handleRequest() {
		if (!$session.topicId) return;
		transfer = await requestTransfer($session.topicId);
	}

	async function handleCancel() {
		if (!$session.topicId) return;
		await cancelTransfer($session.topicId);
		transfer = null;
	}
</script>

<div class="transfer-banner">
	{#if transfer}
		<div class="pending">
			<p>Creator transfer pending — {timeLeft} remaining</p>
			{#if $isCreator}
				<button on:click={handleCancel}>Cancel Transfer</button>
			{/if}
		</div>
	{:else if $isAdmin && !$isCreator}
		<button on:click={handleRequest}>Request Creator Transfer</button>
	{/if}
</div>

<style>
	.transfer-banner { margin: 1rem 0; }
	.pending { background: #fef3c7; border: 1px solid #f59e0b; padding: 0.75rem 1rem; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
	.pending p { margin: 0; }
	button { padding: 0.4rem 0.8rem; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; background: white; }
</style>
