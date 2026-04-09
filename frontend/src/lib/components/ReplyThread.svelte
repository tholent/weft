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
	import type { Reply } from '$lib/types/reply';

	export let replies: Reply[];
	export let isModerator: boolean;
</script>

<div class="reply-thread">
	{#each replies as reply (reply.id)}
		<div class="reply">
			<p class="reply-body">{reply.body}</p>
			<div class="reply-meta">
				<span>{reply.author_handle || 'Anonymous'}</span>
				<span>{new Date(reply.created_at).toLocaleString()}</span>
				{#if reply.wants_to_share}<span class="badge">Shared</span>{/if}
				{#if isModerator}<span class="badge status">{reply.relay_status}</span>{/if}
			</div>
			{#if reply.mod_responses.length > 0}
				<div class="mod-responses">
					{#each reply.mod_responses as mr (mr.id)}
						<div class="mod-response">
							<p>{mr.body}</p>
							<span class="mod-meta">{mr.author_handle || 'Moderator'} · {mr.scope}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/each}
</div>

<style>
	.reply-thread { margin-left: 1rem; border-left: 2px solid #e5e7eb; padding-left: 1rem; }
	.reply { margin: 0.5rem 0; }
	.reply-body { margin: 0 0 0.25rem; }
	.reply-meta { font-size: 0.8rem; color: #666; display: flex; gap: 0.5rem; align-items: center; }
	.badge { background: #e5e7eb; padding: 0.1rem 0.4rem; border-radius: 3px; font-size: 0.75rem; }
	.status { text-transform: capitalize; }
	.mod-responses { margin-left: 1rem; margin-top: 0.5rem; }
	.mod-response { background: #fef3c7; padding: 0.5rem; border-radius: 4px; margin: 0.25rem 0; }
	.mod-response p { margin: 0 0 0.25rem; }
	.mod-meta { font-size: 0.75rem; color: #92400e; }
</style>
