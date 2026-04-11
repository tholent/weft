# Frontend test suite

This directory contains two layers of tests:

- **Unit** — Vitest specs under [`tests/unit/`](./unit) that exercise stores,
  API wrappers, Svelte components, and small utilities in a jsdom environment.
  ~338 tests across 26 files.
- **End-to-end** — Playwright specs under [`tests/e2e/`](./e2e) that drive the
  built SPA against a real FastAPI backend. ~122 active tests, 14 intentionally
  skipped (see the skipped-tests reference at the bottom of this file).

Backend tests live in [`../../backend/tests/`](../../backend/tests) and are
separately covered by `Backend CI`.

## Running unit tests

All commands run from `frontend/`.

```bash
# Run once
npm run test:unit

# Watch mode — re-run on file changes
npm run test:unit -- --watch

# With coverage (lcov + text reporters)
npm run test:coverage

# Single file
npx vitest run tests/unit/stores/session.test.ts

# Single test by name
npx vitest run -t "isAuthenticated"
```

Notes:

- The `test:unit` / `test:coverage` scripts are wrapped with `ulimit -c 0` so a
  crashing child does not leave multi-GB core dumps in the working directory.
- The environment is jsdom with a synthetic URL of `http://localhost/` (set via
  `environmentOptions.jsdom.url` in `vite.config.ts`) so relative `fetch('/api/...')`
  calls resolve to an absolute URL that MSW can intercept.
- MSW is configured in `tests/unit/setup.ts` with `onUnhandledRequest: 'error'`,
  so any test that fires an unmocked request fails loudly.
- `tests/unit/fixtures/` contains typed factory functions (`makeTopic`,
  `makeCircle`, `makeMember`, `makeUpdate`, `makeReply`, `makeAttachment`,
  `makeNotificationPreference`, `makeAuthResponse`) that produce deterministic
  objects matching the shared TypeScript types. Use these instead of inline
  literals in new tests.
- `tests/unit/mocks/` has reusable mocks for `$app/stores`, `$app/navigation`,
  and the MSW server.

## Running E2E tests

```bash
# Full suite (both chromium-desktop and chromium-mobile projects)
npm run test:e2e

# One project
npx playwright test --project=chromium-desktop
npx playwright test --project=chromium-mobile

# One spec file
npx playwright test tests/e2e/landing.spec.ts

# Grep by test name
npx playwright test -g "admin"

# Headed (visible browser)
npx playwright test --headed

# Interactive UI mode
npx playwright test --ui
```

### How the backend is booted

Playwright's `webServer` runs
[`scripts/start-e2e.sh`](../scripts/start-e2e.sh), which:

1. Sets `ulimit -c 0` so crashes don't produce core dumps.
2. Resolves the frontend and backend directories relative to its own path, so
   the script works both locally (`/workspace/...`) and in GitHub Actions
   (`$GITHUB_WORKSPACE/...`).
3. Exports the shared env vars:
   - `ENV=test` — gates the test-seed router mount (see below).
   - `DATABASE_URL=sqlite+aiosqlite:////tmp/weft_e2e.db` — fresh DB each run.
   - `SECRET_KEY=e2e-test-secret-key-do-not-use-in-prod`
   - `BASE_URL=http://127.0.0.1:4173` — the CORS-allowed origin, i.e. the
     preview server.
   - `ATTACHMENT_MAX_SIZE_BYTES=2048` — keeps the oversize fixture tiny.
   - `UV_PROJECT_ENVIRONMENT=$BACKEND_DIR/.venv`
4. Removes `/tmp/weft_e2e.db` and runs `alembic upgrade head` on a fresh file.
5. Starts `uvicorn app.main:app` on 127.0.0.1:8001 in the background.
6. Runs `VITE_API_BASE=http://127.0.0.1:8001 npm run build`, so the preview
   bundle points at the right API origin.
7. Starts `npm run preview -- --port 4173 --host 127.0.0.1` in the background.
8. Traps `EXIT`/`INT`/`TERM` to kill both children, then `wait`s so Playwright
   can connect.

### Test-seed router (test-only)

The backend exposes `POST /test/seed/reset` and `POST /test/seed/topic` **only
when `settings.env == "test"`**. The router module is imported inside an `if`
block in `app/main.py` — the code is never loaded in production. Each handler
also re-verifies `settings.env` defensively.

From E2E specs you use it via the typed wrapper in
[`tests/e2e/fixtures/seed-client.ts`](./e2e/fixtures/seed-client.ts) or the
shared Playwright fixture `seededTopic`, which reset the DB and create a
default topic with one circle, two recipients, an admin, and a moderator
before each test. If you need a different topology, call `seedClient` directly:

```ts
test('two circles', async ({ page, seedClient }) => {
  await seedClient.reset();
  const seed = await seedClient.seedTopic({
    title: 'Two circle topic',
    owner_email: 'owner@example.com',
    owner_name: 'Owner',
    circles: [
      { name: 'Family', members: [{ email: 'alice@example.com', role: 'recipient' }] },
      { name: 'Coworkers', members: [{ email: 'bob@example.com', role: 'recipient' }] },
    ],
    updates: [
      { body: 'Hi family', circle_names: ['Family'], author_email: 'owner@example.com' },
    ],
  });
  // ... seed.magic_links.owner / seed.magic_links.recipients['alice@example.com']
});
```

The response includes raw bearer tokens AND signed magic-link tokens for every
seeded member, so tests can either drive the real `/auth?t=...` flow or call
backend endpoints directly via `page.request` with the bearer.

### Worker count

`playwright.config.ts` sets `fullyParallel: false` and `workers: 1`. Every test
in the suite resets and re-seeds the same SQLite database, so running workers
concurrently would race. Each spec runs sequentially until per-worker
databases are introduced.

## Debugging a failing Playwright test

```bash
# Pause at every action so you can inspect the page in DevTools
PWDEBUG=1 npx playwright test tests/e2e/landing.spec.ts

# Interactive UI runner — best for iterating on selectors
npx playwright test --ui

# Headed mode without the debugger
npx playwright test --headed tests/e2e/landing.spec.ts

# Open an HTML trace after a failure
npx playwright show-trace test-results/<spec>-chromium-desktop/trace.zip
```

Artifacts after a failed run:

- `test-results/<test-id>/` — screenshots, traces, error context, and any video
  captured for the failing test. Gitignored.
- `playwright-report/` — HTML report aggregated across the run. Gitignored.
  Open with `npx playwright show-report`.

When a test fails in CI, the `playwright-report/` and `test-results/` artifacts
are uploaded by the workflow on failure (see `.github/workflows/frontend.yml`)
and visible on the run summary page.

## Gotchas

The following are real footguns that have bitten contributors — if you're
writing new tests, skim this section first.

### Svelte 5 + @testing-library/svelte

`@testing-library/svelte` **v5** is required; v4 does not work. The version is
pinned in `package.json`.

`vite.config.ts` also sets `resolve.conditions: ['browser']`. Without this,
Vitest resolves `svelte` to its **server** build inside jsdom and every
component mount crashes with `lifecycle_function_unavailable`. Do not remove
that line.

### Mocking `$app/stores` and `$app/navigation`

Use the helpers in [`tests/unit/mocks/sveltekit.ts`](./unit/mocks/sveltekit.ts):

```ts
import { vi } from 'vitest';
import { mockPageStore, mockGoto } from '../mocks/sveltekit';

const gotoSpy = mockGoto();
const pageStore = mockPageStore({ url: new URL('http://localhost/topic/abc') });

vi.mock('$app/navigation', () => ({ goto: gotoSpy }));
vi.mock('$app/stores', () => ({ page: pageStore }));
```

`vi.mock` is **hoisted** above all imports, so any variables the factory
references must be defined at the top of the module — declare `gotoSpy` and
`pageStore` before the `vi.mock` call. `tests/unit/mocks/sveltekit.test.ts`
has the canonical working example.

### Async user interactions

Always `await` Testing Library interactions:

```ts
// ✓ good
await fireEvent.click(button);
await userEvent.type(input, 'hello');

// ✗ bad — Svelte reactive updates have not flushed yet
fireEvent.click(button);
expect(screen.getByText('after click')).toBeVisible();  // flaky!
```

For state updates triggered by async code (MSW responses, `onMount` fetches),
wrap assertions in `waitFor`:

```ts
await waitFor(() => {
  expect(screen.getByText(/loaded/i)).toBeInTheDocument();
});
```

### localStorage reset between tests

`tests/unit/setup.ts` runs `beforeEach(() => localStorage.clear())`. If your
test needs to prime localStorage, do it **inside the test body**, not at module
scope — otherwise the value is wiped before your test runs.

For the `session.ts` store specifically: it reads `localStorage` at module
load time, so to test the initial-state path you need `vi.resetModules()` +
dynamic `await import('$lib/stores/session')` **after** priming. See
`tests/unit/stores/session.test.ts` for the pattern.

### jsdom missing APIs

jsdom does not implement `URL.createObjectURL`, `URL.revokeObjectURL`, or
reliable `Blob.text()` / `Blob.arrayBuffer()`. Two real cases to know about:

```ts
// Define stubs BEFORE vi.spyOn — otherwise spyOn fails with
// "createObjectURL does not exist"
if (typeof URL.createObjectURL !== 'function') {
  Object.defineProperty(URL, 'createObjectURL', {
    value: () => '',
    writable: true,
    configurable: true,
  });
}
const spy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:fake');
```

```ts
// To read back what was passed to new Blob(...), spy on the constructor.
const original = globalThis.Blob;
const calls: { parts: BlobPart[]; type: string | undefined }[] = [];
globalThis.Blob = vi.fn((parts, options) => {
  calls.push({ parts, type: options?.type });
  return new original(parts, options);
}) as unknown as typeof Blob;
```

`tests/unit/api/export.test.ts` uses both patterns.

### MSW handler URLs

MSW handlers should be registered at absolute URLs whose base matches the
jsdom environment URL:

```ts
server.use(
  http.post('http://localhost/api/topics/topic-1/members', async ({ request }) => {
    // ...
  }),
);
```

A bare `'/api/topics/topic-1/members'` path works in some MSW versions but not
all — prefer the absolute form. If you see `[MSW] Error: intercepted a request
without a matching request handler`, double-check the URL.

### API wrappers must use the VITE_API_BASE shim

Any new module under `src/lib/api/` must compute `API_BASE` via the same shim
used by `client.ts`:

```ts
const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';
```

A hardcoded `'/api'` breaks E2E builds, which serve the SPA at 4173 and the
backend at 8001. `attachments.ts` hit this exact bug — it was fixed during
FT-33 but is worth mentioning because it is easy to reintroduce.

### Core dumps

Both `npm run test:unit` and `scripts/start-e2e.sh` set `ulimit -c 0`. If you
add a new test runner script, inherit or re-apply that limit so crashes don't
produce multi-GB core files.

### Strict-mode locator collisions

Playwright's locators default to strict mode — if `page.getByText('Circles')`
matches two elements (e.g., the nav tab and an in-page filter button), the
test fails. Scope to a container:

```ts
// ✓ disambiguate by parent role
await page.getByRole('navigation').getByRole('button', { name: /^circles$/i }).click();

// ✓ disambiguate by CSS class
await expect(page.locator('.section-label', { hasText: 'Export' })).toBeVisible();
```

## Policy: route `+page.svelte` files are E2E-covered only

The following route files are deliberately **not** unit-tested:

- `src/routes/+page.svelte` (landing)
- `src/routes/auth/+page.svelte` (magic-link verify)
- `src/routes/manage/[token]/+page.svelte` (admin/moderator view)
- `src/routes/topic/[token]/+page.svelte` (recipient view)

They mount multiple Svelte stores, fire multiple `onMount` fetches, orchestrate
navigation, and read URL params — all fragile under jsdom. Exercising them
end-to-end through Playwright is both simpler and more faithful to production.

Component unit tests live only for reusable components under
`src/lib/components/`. When adding a new route, add E2E coverage in
`tests/e2e/` rather than mounting the page in Vitest.

## Skipped tests reference

14 E2E tests are intentionally `test.skip`'d because they exercise unreachable
product states or missing UI. Each has a detailed comment in the spec file
explaining why. Summary:

| Spec | Count | Reason |
|---|---|---|
| `moderator-reply-flow.spec.ts` | 2 | No mod-response submission form exists in `ReplyThread.svelte` yet. |
| `transfer-flow.spec.ts` | 2 | The dead-man switch in `app/deps.py` auto-cancels any pending transfer the moment the owner authenticates, so the owner-side Cancel button is dead code. |
| `close-topic.spec.ts` | 4 | After close, `TopicMemberDep` rejects every read of the topic with HTTP 403, so the frontend can't fetch member or topic state to verify the purge or render a "closed" banner. The purge itself is verified by `backend/tests/test_purge.py`. |
| `error-and-empty-states.spec.ts` | 2 | The owner is always a member of their own topic, so the "No members yet." empty state is unreachable from the owner's view. |
| `mobile-viewport.spec.ts` | 4 | File-level `test.beforeEach` skips all tests when running under `chromium-desktop`. They run in `chromium-mobile`. |

When any of the dead-code product states above are implemented or removed,
update the corresponding `test.skip` to either a real assertion or a deletion.
