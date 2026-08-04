# API reference — <project name>

<!--
Developer-facing (integrators). Rules that keep this document trustworthy:
- Every example request/response is CAPTURED from the running API and scrubbed —
  never typed from memory or from reading the handler code. Handlers lie by omission
  (middleware, serializers, error wrappers all shape the real response).
- Behavior not yet verified is marked "unverified", not guessed.
- Error cases are documented with the same care as success — integrators live in the
  error cases.
-->

**Base URL:** `<url>`
**Authentication:** <scheme; how to obtain credentials; what an unauthenticated call returns — captured>
**As of:** YYYY-MM-DD, <version/commit>

## Conventions

- **Errors:** <the actual error envelope, captured, with fields explained>
- **Pagination / limits:** <how, and the enforced caps>
- **Versioning / compatibility:** <the actual promise, or "no versioning — breaking
  changes possible" if that's the truth>

## Endpoints

### `<METHOD> <path>`

<One line: what it's for.>

- **Auth:** <required level>
- **Parameters:**

| Name | In | Type | Required | Notes |
|---|---|---|---|---|
| `<param>` | path/query/body | | | <validation rules as enforced, e.g. regex, clamps> |

**Request:**

```http
<captured example>
```

**Response `200`:**

```json
<captured, scrubbed example>
```

**Errors:**

| Status | When | Body |
|---|---|---|
| `4xx` | <actual trigger> | <captured shape> |

<Repeat per endpoint.>
