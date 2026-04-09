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
