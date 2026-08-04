#!/usr/bin/env node
// PreToolUse hook — blocks literal secret values landing in code, config, commands,
// or outbound tool calls (house rule: vault or it doesn't exist).
// Exit 2 = block; stderr is fed back to Claude as an instruction.
// Fails open (exit 0) on unexpected input so a schema drift never bricks the session.

'use strict';

// Values that are clearly placeholders get a pass — the rule targets real secrets,
// not documentation. Tested against the match plus a short preceding window.
const PLACEHOLDER =
  /(example|sample|placeholder|your[_-]?|x{4,}|test[_-]?(key|token|secret)|dummy|fake|redacted|changeme|<[^>]*>|\$\{|%[A-Z_]+%|process\.env|import\.meta\.env|os\.environ|getenv|\*{3,})/i;

const RULES = [
  { name: 'private key block', re: /-----BEGIN [A-Z ]*PRIVATE KEY-----/g },
  { name: 'AWS access key id', re: /\bAKIA[0-9A-Z]{16}\b/g },
  {
    name: 'GitHub token',
    re: /\b(?:ghp|gho|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b/g,
  },
  { name: 'Stripe live key', re: /\b[sr]k_live_[A-Za-z0-9]{16,}\b/g },
  { name: 'Slack token', re: /\bxox[baprs]-[A-Za-z0-9-]{10,}\b/g },
  { name: 'OpenAI/Anthropic-style key', re: /\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{28,}\b/g },
  {
    name: 'JWT',
    re: /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/g,
  },
  {
    name: 'Azure account key / SAS',
    re: /\b(?:AccountKey|SharedAccessSignature)=[A-Za-z0-9+/=%]{20,}/gi,
  },
  {
    name: 'credentialed connection URL',
    re: /\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqps?|mssql):\/\/[^/\s:@'"]+:(?<pw>[^@\s'"]{4,})@/gi,
    // Throwaway dev passwords in local connection strings are everyday noise, not leaks.
    allow: (m) =>
      /^(postgres|password|pass(word)?123?|example|changeme|secret|test|dev|root|admin|mysql|redis|localdev)$/i.test(
        m.groups && m.groups.pw ? m.groups.pw : ''
      ),
  },
  {
    name: 'literal secret assignment',
    re: /\b(?:api[_-]?key|apikey|secret|token|password|passwd|client[_-]?secret|access[_-]?key|auth[_-]?token)["']?\s*[:=]\s*["'][A-Za-z0-9+/_.\-]{20,}["']/gi,
  },
];

// Local secret stores are where values are SUPPOSED to live — writing there is compliance,
// not a leak. (.env*, local.settings.json for Azure Functions.)
const ALLOWED_TARGETS = /^(\.env(\..+)?|local\.settings\.json)$/i;

function collectStrings(value, out) {
  if (typeof value === 'string') out.push(value);
  else if (Array.isArray(value)) value.forEach((v) => collectStrings(v, out));
  else if (value && typeof value === 'object')
    Object.values(value).forEach((v) => collectStrings(v, out));
}

function scan(text) {
  for (const rule of RULES) {
    rule.re.lastIndex = 0;
    let m;
    while ((m = rule.re.exec(text)) !== null) {
      if (rule.allow && rule.allow(m)) continue;
      const windowStart = Math.max(0, m.index - 40);
      const context = text.slice(windowStart, m.index + m[0].length);
      if (PLACEHOLDER.test(context)) continue;
      return { rule: rule.name, preview: m[0].slice(0, 8) + '…' + ` (${m[0].length} chars)` };
    }
  }
  return null;
}

function main(input) {
  const toolName = input.tool_name || '';
  const ti = input.tool_input || {};

  const targetPath = ti.file_path || ti.notebook_path || '';
  const base = String(targetPath).replace(/\\/g, '/').split('/').pop() || '';
  if (base && ALLOWED_TARGETS.test(base)) process.exit(0);

  // Scan only what this call ADDS. old_string is existing content — scanning it
  // would block the removal of a secret, the one edit we most want to allow.
  const texts = [];
  if (toolName === 'Bash' || toolName === 'PowerShell') {
    if (typeof ti.command === 'string') texts.push(ti.command);
  } else if (toolName === 'Write') {
    if (typeof ti.content === 'string') texts.push(ti.content);
  } else if (toolName === 'Edit') {
    if (typeof ti.new_string === 'string') texts.push(ti.new_string);
  } else if (toolName === 'MultiEdit') {
    (ti.edits || []).forEach((e) => {
      if (e && typeof e.new_string === 'string') texts.push(e.new_string);
    });
  } else if (toolName === 'NotebookEdit') {
    if (typeof ti.new_source === 'string') texts.push(ti.new_source);
  } else {
    collectStrings(ti, texts); // MCP and anything else: all outbound strings
  }

  const hit = scan(texts.join('\n'));
  if (!hit) process.exit(0);

  process.stderr.write(
    `BLOCKED — literal secret detected (${hit.rule}: ${hit.preview}) in this ${toolName} call.\n` +
      `House rule: vault or it doesn't exist. Secret values never land in code, config, commands, or outbound messages — ` +
      `they live in the environment or a key vault and are referenced by NAME (process.env.X, os.environ["X"], ` +
      `@Microsoft.KeyVault(...), az --settings @file, $env:X).\n` +
      `Do this instead: have the value placed in .env / local.settings.json / the vault (those targets are allowed), ` +
      `reference it by name, and record who owns the key.\n` +
      `If this was meant as a placeholder, make it unmistakably fake (YOUR_API_KEY, sk_live_EXAMPLE) and retry.`
  );
  process.exit(2);
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
