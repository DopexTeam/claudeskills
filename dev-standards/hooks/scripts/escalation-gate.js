#!/usr/bin/env node
// PreToolUse hook — the §7 escalation stop-list. Forces a human permission prompt
// ("ask") for actions the session must never take on its own judgment, even when an
// allowlist rule or permissive mode would otherwise auto-approve.
// It never denies and never allows — the decision belongs to the human.
// Fails open (exit 0 / no decision) so normal permission flow applies when unsure.

'use strict';

// Categories mirror SKILLS-MANIFEST §7. Items 2 and 5 (production judgment, settled
// decisions) are only partly mechanical — the SessionStart protocol carries the rest.
const RULES = [
  {
    cat: 1,
    label: 'irreversible / destructive',
    patterns: [
      { re: /\brm\s+(?:-[A-Za-z]+\s+)*-[A-Za-z]*r[A-Za-z]*\b/, hint: 'recursive rm' },
      { re: /\brm\s+[^|;&\n]*(?:\*|\s\/(?:[a-z]|$))/i, hint: 'rm with wildcard or root-level path' },
      { re: /\bRemove-Item\b[^|;\n]*-Recurse\b/i, hint: 'Remove-Item -Recurse' },
      { re: /\b(?:rmdir|rd)\s+\/s\b/i, hint: 'rmdir /s' },
      { re: /\bdel\s+(?:\/[a-z]+\s+)*\/s\b/i, hint: 'del /s' },
      { re: /\bgit\s+push\b[^|;&\n]*(?:--force(?:-with-lease)?\b|\s-f\b)/, hint: 'git force-push' },
      { re: /\bgit\s+reset\s+--hard\b/, hint: 'git reset --hard' },
      { re: /\bgit\s+clean\b[^|;&\n]*-[A-Za-z]*f/, hint: 'git clean -f' },
      { re: /\bgit\s+branch\s+-D\b/, hint: 'git branch -D' },
      { re: /\bdrop\s+(?:table|database|schema|index|view)\b/i, hint: 'SQL DROP' },
      { re: /\btruncate\s+(?:table\s+)?[\w"[\]]/i, hint: 'SQL TRUNCATE' },
      { re: /\bdelete\s+from\b(?![^;|\n]*\bwhere\b)/i, hint: 'DELETE without WHERE' },
      { re: /\bkubectl\s+delete\b/i, hint: 'kubectl delete' },
      { re: /\b(?:az|aws|gcloud)\b[^|;&\n]*\b(?:delete|purge)\b/i, hint: 'cloud resource delete/purge' },
      { re: /\bterraform\s+destroy\b/i, hint: 'terraform destroy' },
      { re: /\b(?:mkfs|format\s+[a-z]:)/i, hint: 'disk format' },
    ],
  },
  {
    cat: 2,
    label: 'production deploy / publish',
    patterns: [
      { re: /\bvercel\b[^|;&\n]*--prod\b/i, hint: 'vercel --prod' },
      { re: /\bnpm\s+publish\b/i, hint: 'npm publish' },
      { re: /\bdocker\s+push\b/i, hint: 'docker push' },
      { re: /\bterraform\s+apply\b/i, hint: 'terraform apply' },
      { re: /\bfunc\s+azure\s+functionapp\s+publish\b/i, hint: 'Azure Functions publish' },
      { re: /--slot\s+production\b/i, hint: 'production slot' },
      { re: /\bgh\s+release\s+create\b/i, hint: 'GitHub release' },
    ],
  },
  {
    cat: 3,
    label: 'security posture change',
    patterns: [
      { re: /\baz\b[^|;&\n]*\brole\s+assignment\b/i, hint: 'Azure role assignment' },
      { re: /\bfirewall-rule\s+(?:create|update|delete)\b/i, hint: 'firewall rule change' },
      { re: /\bchmod\s+(?:-[A-Za-z]+\s+)*0?777\b/, hint: 'chmod 777' },
      { re: /\bicacls\b[^|;\n]*\/grant\b[^|;\n]*everyone/i, hint: 'icacls grant Everyone' },
      { re: /\bgrant\s+(?:all|select|insert|update|delete|execute)\b[^;|\n]*\bto\b/i, hint: 'SQL GRANT' },
      { re: /\bdisable\s+row\s+level\s+security\b/i, hint: 'RLS disable' },
      { re: /\b(?:create|alter)\s+(?:user|login|role)\b/i, hint: 'SQL principal change' },
    ],
  },
  {
    cat: 4,
    label: 'spend / money movement',
    patterns: [
      { re: /\b(?:az|aws|gcloud)\b[^|;&\n]*\b(?:create|new)\b/i, hint: 'cloud resource creation' },
      { re: /\bstripe\b[^|;&\n]*--live\b/i, hint: 'Stripe live mode' },
    ],
  },
  {
    cat: 6,
    label: 'credential acquisition',
    patterns: [
      { re: /\b(?:az|gcloud)\s+(?:login|auth\s+login)\b/i, hint: 'cloud login' },
      { re: /\baws\s+configure\b/i, hint: 'aws configure' },
      { re: /\bgh\s+auth\s+login\b/i, hint: 'gh auth login' },
    ],
  },
];

// MCP tools get a name-based screen: destructive or money-moving verbs force a human look.
const MCP_TOOL_NAME =
  /(delete|remove|destroy|drop|purge|pay|charge|refund|transfer|payout)/i;

function collectStrings(value, out) {
  if (typeof value === 'string') out.push(value);
  else if (Array.isArray(value)) value.forEach((v) => collectStrings(v, out));
  else if (value && typeof value === 'object')
    Object.values(value).forEach((v) => collectStrings(v, out));
}

function ask(reason) {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'ask',
        permissionDecisionReason: reason,
      },
    })
  );
  process.exit(0);
}

function main(input) {
  const toolName = input.tool_name || '';
  const ti = input.tool_input || {};

  if (toolName.startsWith('mcp__')) {
    const m = MCP_TOOL_NAME.exec(toolName);
    if (m) {
      ask(
        `Escalation stop-list (house standard): MCP tool '${toolName}' looks ${
          /(pay|charge|refund|transfer|payout)/i.test(m[0]) ? 'money-moving (#4)' : 'destructive (#1)'
        }. A human must approve this call.`
      );
    }
  }

  const texts = [];
  if (typeof ti.command === 'string') texts.push(ti.command);
  else collectStrings(ti, texts);
  const haystack = texts.join('\n');
  if (!haystack) process.exit(0);

  for (const rule of RULES) {
    for (const p of rule.patterns) {
      if (p.re.test(haystack)) {
        ask(
          `Escalation stop-list #${rule.cat} (${rule.label}): detected ${p.hint}. ` +
            `The house standard requires a human decision here — this prompt is that decision. ` +
            `If declined, log the alternative taken to ASSUMPTIONS.md.`
        );
      }
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
    process.exit(0); // fail open — normal permission flow still applies
  }
});
