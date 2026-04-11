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

import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	// The 'browser' condition forces Vite (and Vitest) to resolve Svelte 5 to
	// its client build inside jsdom. Without it, component tests load the
	// server build and crash with `lifecycle_function_unavailable`.
	resolve: {
		conditions: ['browser']
	},
	server: {
		proxy: {
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, '')
			}
		}
	},
	test: {
		environment: 'jsdom',
		globals: true,
		setupFiles: ['./tests/unit/setup.ts'],
		include: ['tests/unit/**/*.test.ts', 'src/**/*.test.ts'],
		environmentOptions: {
			jsdom: {
				url: 'http://localhost/'
			}
		},
		coverage: {
			provider: 'v8',
			// json-summary emits coverage-summary.json, which CI parses to
			// surface the overall coverage percentage in the job summary.
			reporter: ['lcov', 'text', 'json-summary'],
			reportsDirectory: 'coverage',
			include: ['src/**/*.{ts,svelte}'],
			exclude: [
				'src/**/*.test.ts',
				'src/**/*.spec.ts',
				'tests/unit/**',
				'src/app.d.ts',
				// Route page files are E2E-covered only — see tests/README.md
				// "Policy: route +page.svelte files are E2E-covered only".
				// Including them in the Vitest metric drags the number down
				// without reflecting actual coverage gaps.
				'src/routes/**/+page.svelte',
				'src/routes/**/+layout.svelte',
				'src/routes/+layout.ts',
				'src/lib/types/**',
				'**/*.svelte.d.ts'
			]
		}
	}
});
