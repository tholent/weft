<!--
  Copyright 2026 Chris Wells <chris@tholent.com>

  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
-->

<script lang="ts">
	import type { Circle } from '$lib/types/circle';

	export let mode: 'update' | 'reply' | 'mod_response';
	export let targetCircles: Circle[] = [];
	export let onSubmit: (data: Record<string, unknown>) => void;

	let body = '';
	let selectedCircles: string[] = [];
	let wantsToShare = false;
	let scope: 'sender_only' | 'sender_circle' | 'all_circles' = 'sender_only';

	let customEnabled: Record<string, boolean> = {};
	let customBody: Record<string, string> = {};
	let popoverOpen = false;

	const MAX_VISIBLE = 3;
	$: sortedCircles = [
		...targetCircles.filter((c) => selectedCircles.includes(c.id)),
		...targetCircles.filter((c) => !selectedCircles.includes(c.id))
	];
	$: visibleCircles = sortedCircles.slice(0, MAX_VISIBLE);
	$: overflowCircles = sortedCircles.slice(MAX_VISIBLE);
	$: overflowSelected = overflowCircles.filter((c) => selectedCircles.includes(c.id)).length;

	function handleWindowClick(e: MouseEvent) {
		if (popoverOpen) {
			const target = e.target as Element;
			if (!target.closest('.overflow-wrap')) {
				popoverOpen = false;
			}
		}
	}

	$: hasAnyCustom = selectedCircles.some((id) => customEnabled[id]);

	function toggleCircle(id: string) {
		if (selectedCircles.includes(id)) {
			selectedCircles = selectedCircles.filter((c) => c !== id);
			customEnabled = { ...customEnabled, [id]: false };
		} else {
			selectedCircles = [...selectedCircles, id];
		}
	}

	function toggleCustom(id: string) {
		customEnabled = { ...customEnabled, [id]: !customEnabled[id] };
	}

	function handleSubmit() {
		if (!body.trim()) return;
		if (mode === 'update') {
			const circle_bodies: Record<string, string> = {};
			for (const id of selectedCircles) {
				if (customEnabled[id] && customBody[id]?.trim()) {
					circle_bodies[id] = customBody[id].trim();
				}
			}
			onSubmit({ body: body.trim(), circle_ids: selectedCircles, circle_bodies });
			body = '';
			customEnabled = {};
			customBody = {};
			selectedCircles = [];
		} else if (mode === 'reply') {
			onSubmit({ body, wants_to_share: wantsToShare });
			body = '';
		} else {
			onSubmit({ body, scope });
			body = '';
		}
	}
</script>

<svelte:window on:click={handleWindowClick} />

<form class="compose" on:submit|preventDefault={handleSubmit}>
	<textarea
		bind:value={body}
		placeholder={mode === 'update'
			? hasAnyCustom ? 'Default message (for circles without a custom message)…' : 'Write an update…'
			: mode === 'reply' ? 'Write a reply…' : 'Write a response…'}
		rows="3"
	></textarea>

	{#if mode === 'update' && selectedCircles.some((id) => customEnabled[id])}
		<div class="custom-messages">
			{#each targetCircles.filter((c) => customEnabled[c.id]) as circle (circle.id)}
				<div class="custom-entry">
					<span class="custom-label">{circle.name}</span>
					<textarea
						bind:value={customBody[circle.id]}
						placeholder="Message for {circle.name}…"
						rows="2"
					></textarea>
				</div>
			{/each}
		</div>
	{/if}

	<div class="footer">
		{#if mode === 'update' && targetCircles.length > 0}
			<div class="circle-pills">
				{#each visibleCircles as circle (circle.id)}
					{@const selected = selectedCircles.includes(circle.id)}
					<span class="pill-wrap" class:selected class:has-alt={selected && customEnabled[circle.id]}>
						<button type="button" class="circle-pill" on:click={() => toggleCircle(circle.id)}>{circle.name}</button>
						{#if selected}
							<button
								type="button"
								class="pill-alt"
								class:active={customEnabled[circle.id]}
								on:click={() => toggleCustom(circle.id)}
								title="Custom message for {circle.name}"
							>ALT</button>
						{/if}
					</span>
				{/each}
				{#if overflowCircles.length > 0}
					<div class="overflow-wrap">
						<button
							type="button"
							class="overflow-btn"
							class:has-selected={overflowSelected > 0}
							on:click|stopPropagation={() => (popoverOpen = !popoverOpen)}
						>{overflowSelected > 0 ? `+${overflowSelected}` : '+'}</button>
						{#if popoverOpen}
							<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
							<div class="popover" on:click|stopPropagation>
								{#each overflowCircles as circle (circle.id)}
									{@const selected = selectedCircles.includes(circle.id)}
									<div class="popover-row">
										<span class="pill-wrap" class:selected class:has-alt={selected && customEnabled[circle.id]}>
											<button type="button" class="circle-pill" on:click={() => toggleCircle(circle.id)}>{circle.name}</button>
											{#if selected}
												<button
													type="button"
													class="pill-alt"
													class:active={customEnabled[circle.id]}
													on:click={() => toggleCustom(circle.id)}
													title="Custom message for {circle.name}"
												>ALT</button>
											{/if}
										</span>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{/if}

		{#if mode === 'reply'}
			<label class="share-check">
				<input type="checkbox" bind:checked={wantsToShare} />
				Share with group
			</label>
		{/if}

		{#if mode === 'mod_response'}
			<select bind:value={scope}>
				<option value="sender_only">Sender only</option>
				<option value="sender_circle">Sender's circle</option>
				<option value="all_circles">All circles</option>
			</select>
		{/if}

		<button type="submit" class="send-btn">Send</button>
	</div>
</form>

<style>
	.compose { display: flex; flex-direction: column; gap: 0.5rem; margin: 0.5rem 0; }
	textarea { padding: 0.5rem; border: 1px solid var(--color-border); border-radius: 4px; font-family: inherit; resize: vertical; width: 100%; box-sizing: border-box; }

	.custom-messages { display: flex; flex-direction: column; gap: 0.5rem; }
	.custom-entry { display: flex; flex-direction: column; gap: 0.2rem; }
	.custom-label { font-size: var(--text-xs); font-weight: 600; color: var(--color-accent); text-transform: uppercase; letter-spacing: 0.04em; }

	.footer { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }

	.circle-pills { display: flex; align-items: center; gap: 0.25rem; flex: 1; flex-wrap: wrap; }
	.pill-wrap {
		display: inline-flex; align-items: stretch;
		border: 1px solid var(--color-border-strong); border-radius: 4px;
		overflow: hidden; transition: all 0.1s;
	}
	.pill-wrap.selected {
		background: var(--color-accent-light); border-color: var(--color-accent);
	}
	.circle-pill {
		background: none; border: none; border-radius: 0;
		padding: 0.2rem 0.65rem; font-size: var(--text-xs);
		color: var(--color-text-secondary); cursor: pointer;
	}
	.pill-wrap.selected .circle-pill { color: var(--color-accent); }
	.pill-alt {
		display: inline-flex; align-items: center; align-self: stretch;
		background: color-mix(in srgb, var(--color-accent-light) 40%, var(--color-surface)); border: none;
		border-left: 1px solid #f0d0b0;
		padding: 0 0.35rem;
		font-size: 0.55rem; font-weight: 700; letter-spacing: 0.06em;
		color: color-mix(in srgb, var(--color-accent) 55%, var(--color-surface)); cursor: pointer; transition: all 0.1s;
	}
	.pill-alt.active { background: var(--color-accent); border-left-color: var(--color-accent); color: white; }

	.overflow-wrap { position: relative; display: inline-flex; align-items: center; }
	.overflow-btn {
		padding: 0.2rem 0.55rem; border-radius: 4px; font-size: var(--text-xs);
		border: 1px solid var(--color-border-strong); background: none;
		color: var(--color-text-secondary); cursor: pointer; transition: all 0.1s; white-space: nowrap;
	}
	.overflow-btn.has-selected { background: var(--color-accent-light); border-color: var(--color-accent); color: var(--color-accent); }
	.popover {
		position: absolute; bottom: calc(100% + 0.35rem); left: 0;
		background: var(--color-surface); border: 1px solid var(--color-border);
		border-radius: 6px; padding: 0.5rem; z-index: 50;
		display: flex; flex-direction: column; gap: 0.3rem;
		box-shadow: 0 4px 12px rgba(0,0,0,0.12); min-width: 140px;
	}
	.popover-row { display: flex; align-items: center; gap: 0.25rem; }

	.share-check { display: flex; align-items: center; gap: 0.25rem; font-size: var(--text-sm); white-space: nowrap; }
	select { padding: 0.3rem 0.4rem; border: 1px solid var(--color-border); border-radius: 4px; font-size: var(--text-sm); }
	.send-btn { margin-left: auto; padding: 0.4rem 1rem; background: var(--color-text); color: white; border: none; border-radius: 4px; cursor: pointer; transition: background 0.15s; white-space: nowrap; }
	.send-btn:hover { background: var(--color-accent); }
</style>
