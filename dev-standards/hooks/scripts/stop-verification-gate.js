#!/usr/bin/env node
// Stop hook — fast deterministic verification gate (SKILLS-MANIFEST §6).
// Blocks exactly one pattern: files were edited this turn, the final message claims
// completion, and no check-capable tool ran after the last edit. Pure Q&A turns,
// honest "unverified" reports, and edit-then-check turns always pass.
// Deliberately a command hook, not an LLM hook: it must stay fast enough to never
// be worth disabling. Fails open on anything unexpected.

'use strict';

const fs = require('fs');

const EDIT_TOOLS = new Set(['Write', 'Edit', 'MultiEdit', 'NotebookEdit']);
const CHECK_TOOLS = new Set(['Bash', 'PowerShell', 'Agent', 'Task', 'WebFetch']);
const isCheck = (name) => CHECK_TOOLS.has(name) || name.startsWith('mcp__');

const CLAIM =
  /\b(done|complete|completed|finished|fixed|resolved|working(?!\s+on)|works|verified|confirmed|passing|passes|all\s+set|ready\s+to\s+(ship|deploy|merge|go)|implemented|deployed)\b/i;
// An honest report of unverified state is the correct behavior — never punish it.
const HONESTY =
  /\b(unverified|untested|not\s+(?:yet\s+)?(?:verified|tested|run|checked)|haven'?t\s+(?:verified|tested|run|checked)|didn'?t\s+(?:verify|test|run|check)|still\s+needs?\s+(?:verification|testing))\b/i;

const MAX_LINES = 4000; // a turn lives well inside this; beyond it, fail open

function isRealUserPrompt(entry) {
  if (entry.type !== 'user' || !entry.message) return false;
  const c = entry.message.content;
  if (typeof c === 'string') return true;
  return Array.isArray(c) && c.some((b) => b && b.type === 'text');
}

function main(input) {
  if (input.stop_hook_active) process.exit(0); // a stop gate already fired this cycle
  const path = input.transcript_path;
  if (!path || !fs.existsSync(path)) process.exit(0);

  const lines = fs.readFileSync(path, 'utf8').split('\n');
  const start = Math.max(0, lines.length - MAX_LINES);

  // Walk backward to the last real user prompt; the span after it is this turn.
  const turn = [];
  let foundPrompt = false;
  for (let i = lines.length - 1; i >= start; i--) {
    const line = lines[i].trim();
    if (!line) continue;
    let entry;
    try {
      entry = JSON.parse(line);
    } catch (e) {
      continue;
    }
    if (entry.isSidechain || entry.isMeta) continue;
    if (isRealUserPrompt(entry)) {
      foundPrompt = true;
      break;
    }
    if (entry.type === 'assistant' && entry.message) turn.push(entry);
  }
  if (!foundPrompt || turn.length === 0) process.exit(0);
  turn.reverse(); // chronological

  const toolCalls = [];
  let finalText = '';
  for (const entry of turn) {
    const blocks = Array.isArray(entry.message.content) ? entry.message.content : [];
    const texts = [];
    for (const b of blocks) {
      if (!b) continue;
      if (b.type === 'tool_use' && typeof b.name === 'string') toolCalls.push(b.name);
      if (b.type === 'text' && typeof b.text === 'string') texts.push(b.text);
    }
    if (texts.length) finalText = texts.join('\n'); // keep the LAST text-bearing message
  }

  let lastEdit = -1;
  let lastCheck = -1;
  toolCalls.forEach((name, i) => {
    if (EDIT_TOOLS.has(name)) lastEdit = i;
    if (isCheck(name)) lastCheck = i;
  });

  const violation =
    lastEdit >= 0 && lastCheck < lastEdit && CLAIM.test(finalText) && !HONESTY.test(finalText);
  if (!violation) process.exit(0);

  process.stderr.write(
    'Stop gate (house standard, verification-discipline): files were edited this turn and the final message ' +
      'reports completion, but no check ran after the last edit. Exit codes and clean writes are not proof. ' +
      'Either run the semantic check that proves the claim (build, test, probe, real output shown) and report ' +
      'its actual result, or restate the status honestly as unverified.'
  );
  process.exit(2);
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
