# Adapter template — the shape, with code

TypeScript-flavored pseudocode; translate idiomatically. The parts are load-bearing,
the syntax isn't.

## 1. The interface — domain verbs, domain types

```ts
// The app's view of Procore. No vendor vocabulary leaks past this file.
export interface ConstructionSystemAdapter {
  getOpenInvoices(projectRef: ProjectRef): Promise<Invoice[]>;
  getProject(ref: ProjectRef): Promise<Project>;
  submitInvoiceStatus(ref: InvoiceRef, status: InvoiceStatus): Promise<void>;
}
// Domain types (Invoice, ProjectRef, ...) are YOURS — the adapter maps the
// vendor's payloads into them and normalizes pagination away entirely.
```

## 2. Typed errors — policy without vendor knowledge

```ts
export type AdapterErrorKind =
  | "retryable"      // timeouts, 5xx, network — safe to retry with backoff
  | "rate_limited"   // retryable, but honor Retry-After
  | "auth_expired"   // refresh or re-auth, then retry once
  | "permanent";     // 4xx contract violations, validation — do not retry

export class AdapterError extends Error {
  constructor(readonly kind: AdapterErrorKind, message: string,
              readonly cause?: unknown) { super(message); }
}
```

Callers switch on `kind`, never on vendor status codes.

## 3. Config — all-or-nothing at construction

```ts
const REQUIRED = ["PROCORE_CLIENT_ID", "PROCORE_CLIENT_SECRET",
                  "PROCORE_BASE_URL", "PROCORE_COMPANY_ID"] as const;

export function loadProcoreConfig(env = process.env): ProcoreConfig {
  const missing = REQUIRED.filter((k) => !env[k]);
  const present = REQUIRED.filter((k) => env[k]);
  if (missing.length > 0 && present.length > 0)
    throw new Error(
      `Procore adapter half-configured: missing ${missing.join(", ")} ` +
      `(have ${present.join(", ")}). Set all of them, or none and run demo mode.`);
  if (missing.length === REQUIRED.length) return { mode: "unconfigured" };
  return { mode: "configured", /* ...parsed values */ };
}
```

Names in the error, never values. Half-configured throws *here*, at startup — not at
first use, three layers from the cause.

## 4. The live implementation — where vendor reality is absorbed

Responsibilities, each in one place:

- **Auth + token refresh** (OAuth dance, refresh-before-expiry, `auth_expired` on
  failure — retry once after refresh, then surface).
- **Timeouts on every request** — no exceptions.
- **Retries: backoff + jitter, `retryable`/`rate_limited` only,** honoring
  `Retry-After`; a bounded number of attempts; idempotency keys on any mutation.
- **Payload validation at the boundary** (schema-parse the response; a missing field
  is a loud `permanent` error naming the field, not a downstream `undefined`).
- **Error translation** — every catch ends in an `AdapterError`, never a raw vendor
  exception escaping.
- **Webhooks** (when the vendor pushes): verify the signature at the boundary,
  translate the event into a domain event, and process idempotently by event ID —
  redelivery is normal operation.

## 5. The demo implementation — deterministic, realistic, loud

```ts
export class DemoConstructionSystem implements ConstructionSystemAdapter {
  readonly mode = "demo" as const;   // surfaces can (and must) check this
  // Deterministic fixture data: same inputs, same outputs, works offline.
}
```

- **Data is realistic and edge-inclusive** — long vendor names, empty projects, a
  disputed invoice — so the demo doubles as a design-time fixture and as the fake
  that `testing-strategy`'s contract suite pins against the live implementation.
- **It announces itself**: the factory logs `PROCORE ADAPTER: DEMO MODE — fixture
  data, no live connection` at startup, and every UI fed by it renders a visible
  demo banner/watermark keyed off `mode`. Loud is the feature: silently plausible
  demo data eventually gets shown to a client as real.

## 6. The factory — explicit selection, no silent fallback

```ts
export function createConstructionSystem(env = process.env) {
  const selected = env.PROCORE_ADAPTER ?? "demo";   // explicit; default is the
  const config = loadProcoreConfig(env);            // SAFE mode, loudly labeled
  if (selected === "live") {
    if (config.mode !== "configured")
      throw new Error("PROCORE_ADAPTER=live but config incomplete — refusing to start.");
    return new LiveConstructionSystem(config);
  }
  log.warn("PROCORE ADAPTER: DEMO MODE — fixture data, no live connection");
  return new DemoConstructionSystem();
}
```

The two prohibitions the factory encodes: live-with-partial-config never limps, and
**a live failure never downgrades to demo** — fallback-to-demo converts an outage
into a fabrication.
