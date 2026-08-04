#!/usr/bin/env node
// PostToolUse hook — review heuristic, never a blocker (SKILLS-MANIFEST §6).
// Flags business data hardcoded into source files: money-shaped identifiers assigned
// numeric literals, real-looking email addresses, quoted dollar amounts. Behavior
// should come from rows/config so an override never requires a core change.
// Emits additionalContext for Claude to weigh; exits 0 in every case.

'use strict';

const CODE_FILE = /\.(ts|tsx|js|jsx|mjs|cjs|py|cs|vue|svelte)$/i;
const SKIP_FILE = /(\.test\.|\.spec\.|__tests__|__mocks__|fixtures?|\.stories\.)/i;

// Identifiers where a numeric literal usually means a business rule in the wrong home.
const MONEY_ID =
  /\b((?:base|unit|processing|service|late|admin)?[_-]?(?:price|fee|tax|discount|commission|markup|surcharge|wage|salary)\w*)\s*[:=]\s*-?\d[\d_,]*\.?\d*/gi;
// Technical rates are fine; these are not business data.
const TECH_ID = /(rate.?limit|limit.?rate|frame|sample|refresh|baud|bit.?rate|heart|retry|poll)/i;

const EMAIL = /['"`]([\w.+-]+@(?!(?:example|test|acme|domain|email|localhost)\.)[\w-]+\.[a-z]{2,})['"`]/gi;
const DOLLAR_STRING = /['"`]\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?['"`]/g;

function main(input) {
  const ti = input.tool_input || {};
  const filePath = ti.file_path || '';
  if (!CODE_FILE.test(filePath) || SKIP_FILE.test(filePath)) process.exit(0);

  const texts = [];
  if (typeof ti.content === 'string') texts.push(ti.content);
  if (typeof ti.new_string === 'string') texts.push(ti.new_string);
  (ti.edits || []).forEach((e) => {
    if (e && typeof e.new_string === 'string') texts.push(e.new_string);
  });
  const text = texts.join('\n');
  if (!text) process.exit(0);

  const findings = [];
  let m;
  MONEY_ID.lastIndex = 0;
  while ((m = MONEY_ID.exec(text)) !== null) {
    if (!TECH_ID.test(m[1])) findings.push(m[0].trim());
  }
  EMAIL.lastIndex = 0;
  while ((m = EMAIL.exec(text)) !== null) findings.push(m[1]);
  DOLLAR_STRING.lastIndex = 0;
  while ((m = DOLLAR_STRING.exec(text)) !== null) findings.push(m[0]);

  if (!findings.length) process.exit(0);

  const list = findings.slice(0, 5).join(' · ');
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PostToolUse',
        additionalContext:
          `Config-over-code check (house standard, heuristic — not a blocker): ${filePath} now hardcodes ` +
          `what looks like business data (${list}). If this value varies per client, tenant, or deployment, ` +
          `move it to config or the tenant record and read it there — an override should never require a ` +
          `change to core code. If it is genuinely universal (a math constant, a protocol number), leave it ` +
          `and ignore this note.`,
      },
    })
  );
  process.exit(0);
}

let raw = '';
process.stdin.on('data', (d) => (raw += d));
process.stdin.on('end', () => {
  try {
    main(JSON.parse(raw));
  } catch (e) {
    process.exit(0);
  }
});
