#!/usr/bin/env node
// PreToolUse hook — tenant-isolation invariant (house standard, per-project plugin).
// Blocks session-level tenant context: `SET app.*` without LOCAL, and
// set_config('app.*', ..., false). On pooled connections a session-level GUC
// survives the request that set it — the next request on that connection runs
// as the WRONG TENANT. SET LOCAL dies at COMMIT, which is the entire point.
// Exit 2 = block; stderr is fed back to Claude as an instruction.

'use strict';

const RULES = [
  {
    name: 'session-level SET app.*',
    // Matches SET app.x / SET SESSION app.x (also inside ALTER ROLE/DATABASE ... SET app.x,
    // which persists the context even longer). SET LOCAL app.x is the sanctioned form.
    re: /\bSET\s+(?!LOCAL\b)(?:SESSION\s+)?app\s*\.\s*\w+/i,
  },
  {
    name: "set_config('app.*', …, false)",
    // Third argument false = session-level, same leak as SET without LOCAL.
    re: /set_config\s*\(\s*['"]app\.[^'"]+['"]\s*,[^)]*,\s*false\s*\)/i,
  },
];

function collectStrings(value, out) {
  if (typeof value === 'string') out.push(value);
  else if (Array.isArray(value)) value.forEach((v) => collectStrings(v, out));
  else if (value && typeof value === 'object')
    Object.values(value).forEach((v) => collectStrings(v, out));
}

function main(input) {
  const ti = input.tool_input || {};
  const texts = [];
  // Scan everything this call adds or executes; old_string is existing content and
  // scanning it would block the fix.
  if (typeof ti.command === 'string') texts.push(ti.command);
  if (typeof ti.content === 'string') texts.push(ti.content);
  if (typeof ti.new_string === 'string') texts.push(ti.new_string);
  if (typeof ti.new_source === 'string') texts.push(ti.new_source);
  (ti.edits || []).forEach((e) => {
    if (e && typeof e.new_string === 'string') texts.push(e.new_string);
  });
  if (!texts.length) collectStrings(ti, texts);

  const haystack = texts.join('\n');
  for (const rule of RULES) {
    if (rule.re.test(haystack)) {
      process.stderr.write(
        `BLOCKED — ${rule.name} detected. Session-level tenant context leaks across pooled ` +
          `connections: the next request on this connection inherits the previous tenant and reads ` +
          `their data. Use \`SET LOCAL app.tenant_id = ...\` inside the transaction ` +
          `(or set_config('app.tenant_id', $1, true)) so the context dies at COMMIT. ` +
          `The cross-tenant test is the artifact of record — see templates/cross-tenant.test.ts ` +
          `in the multitenant plugin; if this project lacks that test, add it before shipping ` +
          `tenant-scoped queries.`
      );
      process.exit(2);
    }
  }
  process.exit(0);
}

let raw = '';
process.stdin.on('data', (d) => (raw += d));
process.stdin.on('end', () => {
  try {
    main(JSON.parse(raw));
  } catch (e) {
    process.exit(0); // fail open — a broken hook must not brick every tool call
  }
});
