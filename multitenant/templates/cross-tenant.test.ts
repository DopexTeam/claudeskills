/**
 * Cross-tenant isolation test — the artifact of record (house standard).
 *
 * The tenant-guard hook blocks session-level tenant context at write time;
 * this test proves the invariant holds at runtime. A project is not "multi-tenant
 * safe" because RLS policies exist — it is safe when THIS test passes against a
 * pooled connection, because pooling is where the leak lives.
 *
 * Copy into the project's test suite and replace the TODOs. Do not weaken the
 * pooled-reuse test — it is the one that catches the real catastrophe.
 */
import { Pool } from 'pg';
import { describe, it, expect, beforeAll, afterAll } from 'vitest'; // TODO: or jest

// TODO: point at the test database. Never production.
const pool = new Pool({ connectionString: process.env.TEST_DATABASE_URL, max: 1 });
// max: 1 is deliberate — forcing every query through ONE physical connection
// makes any session-level leakage impossible to miss.

const TENANT_A = '00000000-0000-0000-0000-00000000000a'; // TODO: seeded tenant ids
const TENANT_B = '00000000-0000-0000-0000-00000000000b';
const TABLE = 'invoices'; // TODO: a tenant-scoped, RLS-protected table

beforeAll(async () => {
  // TODO: seed one recognizable row per tenant in TABLE.
});

afterAll(async () => {
  await pool.end();
});

async function asTenant<T>(tenantId: string, fn: (client: any) => Promise<T>): Promise<T> {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    // The sanctioned form: LOCAL means the context dies at COMMIT.
    await client.query(`SET LOCAL app.tenant_id = '${tenantId}'`); // TODO: parameterize via set_config($1, $2, true)
    const result = await fn(client);
    await client.query('COMMIT');
    return result;
  } catch (e) {
    await client.query('ROLLBACK');
    throw e;
  } finally {
    client.release();
  }
}

describe('cross-tenant isolation (artifact of record)', () => {
  it('tenant A sees only tenant A rows', async () => {
    const rows = await asTenant(TENANT_A, async (c) =>
      (await c.query(`SELECT tenant_id FROM ${TABLE}`)).rows
    );
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.every((r: any) => r.tenant_id === TENANT_A)).toBe(true);
  });

  it('pooled connection reuse does NOT inherit the previous tenant', async () => {
    // Run a query as tenant A, then reuse the SAME physical connection (max: 1)
    // with no tenant context at all. If SET LOCAL were SET, this second query
    // would silently run as tenant A — the catastrophe this file exists to catch.
    await asTenant(TENANT_A, async (c) => (await c.query(`SELECT 1 FROM ${TABLE}`)).rows);

    const client = await pool.connect();
    try {
      const res = await client.query(`SELECT count(*)::int AS n FROM ${TABLE}`);
      // With RLS enforced and no tenant context, the table must be invisible.
      expect(res.rows[0].n).toBe(0);
      const guc = await client.query(`SELECT current_setting('app.tenant_id', true) AS t`);
      expect(guc.rows[0].t ?? '').toBe(''); // context must not have survived COMMIT
    } finally {
      client.release();
    }
  });

  it('tenant B cannot read tenant A rows even in the same process', async () => {
    const rows = await asTenant(TENANT_B, async (c) =>
      (await c.query(`SELECT tenant_id FROM ${TABLE}`)).rows
    );
    expect(rows.some((r: any) => r.tenant_id === TENANT_A)).toBe(false);
  });
});
