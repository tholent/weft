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
	import { uploadAttachment } from '$lib/api/attachments';
	import { session } from '$lib/stores/session';

	export let mode: 'update' | 'reply' | 'mod_response';
	export let targetCircles: Circle[] = [];
	/** Callback receives form data. For update mode, must return Promise<{ id: string }> so attachments can be uploaded. */
	export let onSubmit: (data: Record<string, unknown>) => Promise<{ id: string }> | Promise<void> | void;

	const MAX_PHOTOS = 5;

	let body = '';
	let selectedCircles: string[] = [];
	let wantsToShare = false;
	let scope: 'sender_only' | 'sender_circle' | 'all_circles' = 'sender_only';

	let customEnabled: Record<string, boolean> = {};
	let customBody: Record<string, string> = {};
	let popoverOpen = false;

	// Photo attachment state
	let photos: File[] = [];
	let photoPreviews: string[] = [];
	let fileInput: HTMLInputElement;
	let uploading = false;
	let uploadError = '';

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

	function handlePhotoClick() {
		fileInput.click();
	}

	function handleFileChange(e: Event) {
		const input = e.target as HTMLInputElement;
		if (!input.files) return;
		const newFiles = Array.from(input.files);
		const remaining = MAX_PHOTOS - photos.length;
		const toAdd = newFiles.slice(0, remaining);
		for (const file of toAdd) {
			photos = [...photos, file];
			const url = URL.createObjectURL(file);
			photoPreviews = [...photoPreviews, url];
		}
		// Reset so the same file can be re-selected
		input.value = '';
	}

	function removePhoto(index: number) {
		URL.revokeObjectURL(photoPreviews[index]);
		photos = photos.filter((_, i) => i !== index);
		photoPreviews = photoPreviews.filter((_, i) => i !== index);
	}

	async function handleSubmit() {
		if (!body.trim()) return;
		uploading = false;
		uploadError = '';

		if (mode === 'update') {
			const circle_ids = selectedCircles.length > 0 ? selectedCircles : targetCircles.map((c) => c.id);
			const circle_bodies: Record<string, string> = {};
			for (const id of selectedCircles) {
				if (customEnabled[id] && customBody[id]?.trim()) {
					circle_bodies[id] = customBody[id].trim();
				}
			}
			const result = await onSubmit({ body: body.trim(), circle_ids, circle_bodies });

			// Upload attachments if we have the update ID
			if (result && photos.length > 0 && $session.topicId) {
				uploading = true;
				const topicId = $session.topicId;
				const updateId = result.id;
				const errors: string[] = [];
				for (const file of photos) {
					try {
						await uploadAttachment(topicId, updateId, file);
					} catch {
						errors.push(file.name);
					}
				}
				uploading = false;
				if (errors.length > 0) {
					uploadError = `Failed to upload: ${errors.join(', ')}`;
				}
			}

			// Revoke preview URLs
			for (const url of photoPreviews) {
				URL.revokeObjectURL(url);
			}
			body = '';
			customEnabled = {};
			customBody = {};
			selectedCircles = [];
			photos = [];
			photoPreviews = [];
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

	{#if mode === 'update' && photoPreviews.length > 0}
		<div class="photo-previews">
			{#each photoPreviews as src, i}
				<div class="photo-thumb-wrap">
					<img class="photo-thumb" {src} alt="Attachment {i + 1}" />
					<button type="button" class="photo-remove" on:click={() => removePhoto(i)} title="Remove photo">×</button>
				</div>
			{/each}
		</div>
	{/if}

	{#if uploadError}
		<p class="upload-error">{uploadError}</p>
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

		{#if mode === 'update'}
			<!-- Hidden file input for photo selection -->
			<input
				bind:this={fileInput}
				type="file"
				accept="image/*"
				multiple
				class="file-input-hidden"
				on:change={handleFileChange}
			/>
			<button
				type="button"
				class="photo-btn"
				disabled={photos.length >= MAX_PHOTOS}
				on:click={handlePhotoClick}
				title={photos.length >= MAX_PHOTOS ? `Maximum ${MAX_PHOTOS} photos` : 'Attach photos'}
			>
				{#if uploading}Uploading…{:else}📎 {photos.length > 0 ? `${photos.length}/${MAX_PHOTOS}` : 'Photo'}{/if}
			</button>
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

		<button type="submit" class="send-btn" disabled={uploading}>Send</button>
	</div>
</form>

<style>
	.compose { display: flex; flex-direction: column; gap: 0.5rem; margin: 0.5rem 0; }
	textarea { padding: 0.5rem; border: 1px solid var(--color-border); border-radius: 4px; font-family: inherit; resize: vertical; width: 100%; box-sizing: border-box; }

	.custom-messages { display: flex; flex-direction: column; gap: 0.5rem; }
	.custom-entry { display: flex; flex-direction: column; gap: 0.2rem; }
	.custom-label { font-size: var(--text-xs); font-weight: 600; color: var(--color-accent); text-transform: uppercase; letter-spacing: 0.04em; }

	.photo-previews {
		display: flex; flex-wrap: wrap; gap: 0.5rem;
	}
	.photo-thumb-wrap {
		position: relative; display: inline-flex;
	}
	.photo-thumb {
		width: 72px; height: 72px; object-fit: cover;
		border-radius: 4px; border: 1px solid var(--color-border);
	}
	.photo-remove {
		position: absolute; top: -6px; right: -6px;
		width: 18px; height: 18px; border-radius: 50%;
		background: var(--color-text); color: white;
		border: none; font-size: 0.75rem; line-height: 1;
		cursor: pointer; display: flex; align-items: center; justify-content: center;
		padding: 0;
	}
	.photo-remove:hover { background: var(--color-danger); }

	.upload-error { font-size: var(--text-xs); color: var(--color-danger); margin: 0; }

	.file-input-hidden { display: none; }

	.photo-btn {
		padding: 0.2rem 0.6rem; border-radius: 4px; font-size: var(--text-xs);
		border: 1px solid var(--color-border-strong); background: none;
		color: var(--color-text-secondary); cursor: pointer; transition: all 0.1s;
		white-space: nowrap;
	}
	.photo-btn:hover:not(:disabled) { background: var(--color-accent-light); border-color: var(--color-accent); color: var(--color-accent); }
	.photo-btn:disabled { opacity: 0.5; cursor: default; }

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
	.send-btn:hover:not(:disabled) { background: var(--color-accent); }
	.send-btn:disabled { opacity: 0.5; cursor: default; }
</style>
