// Copyright 2026 Chris Wells <chris@tholent.com>
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

const API_BASE = '/api';

class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
	}
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
	const token = localStorage.getItem('weft_token');
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...((options.headers as Record<string, string>) || {})
	};
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

	if (res.status === 401) {
		localStorage.removeItem('weft_token');
		window.location.href = '/';
		throw new ApiError(401, 'Unauthorized');
	}

	if (!res.ok) {
		const body = await res.json().catch(() => ({ detail: 'Unknown error' }));
		throw new ApiError(res.status, body.detail || 'Request failed');
	}

	if (res.status === 204) return undefined as T;
	return res.json();
}

export { request, ApiError };
