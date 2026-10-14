"""Comment-aware, paren-aware M surgery for the Procore schema lock."""
import re


def split_line_comment(line):
    """Split on the first `//` that is not inside a string. Returns (code, comment)."""
    inq = False
    i = 0
    while i < len(line):
        c = line[i]
        if inq:
            if c == '"':
                if i + 1 < len(line) and line[i + 1] == '"':
                    i += 1
                else:
                    inq = False
        elif c == '"':
            inq = True
        elif c == '/' and i + 1 < len(line) and line[i + 1] == '/':
            return line[:i], line[i:]
        i += 1
    return line, ""


def upgrade_inline_lock(m, table, step='#"Schema Locked"'):
    """Convert the pre-contract INLINE lock into a LockSchema call.

    The earliest form of this work wrote the column list straight into the step:

        #"Schema Locked" = Table.SelectColumns(prev, {"a","b"}, MissingField.UseNull)

    which null-pads every column and therefore never fails -- every column is
    effectively optional, so a column the report genuinely uses can vanish and
    the refresh still succeeds with wrong numbers. MJS is still on this form.

    Returns (new_m, ok, reason). The head expression is preserved exactly; only
    the call wrapping it is replaced.

    The column list is found with the comment- and string-aware scanner rather
    than a regex, because it spans lines and the surrounding M carries comments
    with unbalanced parens.
    """
    i = m.find(step + " =")
    if i < 0:
        return m, False, "no %s step" % step
    vstart = i + len(step + " =")
    fn = "Table.SelectColumns"
    j = m.find(fn, vstart)
    if j < 0 or m[vstart:j].strip():
        return m, False, "step is not a bare %s call" % fn
    op = j + len(fn)
    end = _scan_call(m, op)
    if end < 0:
        return m, False, "unscannable call"
    args = m[op + 1:end - 1]
    if "MissingField.UseNull" not in args:
        return m, False, "not the inline UseNull form"

    # WRAP the projection, do not replace it.
    #
    # In this form the Table.SelectColumns call is doing two jobs: it is the
    # lock, and it is the PROJECTION that prunes the table to the columns the
    # report uses. v2's LockSchema unions `actual` into its output precisely so
    # that source-added columns flow through, so substituting it for the call
    # drops the projection entirely -- MJS gained 221 columns on the next
    # refresh (PrimeContract 2 -> 129, Project 23 -> 94) as Desktop re-detected
    # the full share schema, undoing a deliberate pruning.
    #
    # Passing the original call as the lock's first argument keeps both
    # behaviours and needs no new step name and no comma surgery.
    projection = m[j:end]
    call = ('LockSchema(%s, SchemaContract[#"%s"][req], SchemaContract[#"%s"][opt])'
            % (projection, table, table))
    return m[:j] + call + m[end:], True, ""


def _scan_call(s, start):
    """start = index of '('; return index just past the matching ')'.

    Skips string literals AND comments -- a comment such as `// 1) parse HTML`
    carries an unmatched ')' that would otherwise close the call early.
    """
    depth = 0
    i = start
    inq = False
    while i < len(s):
        c = s[i]
        if inq:
            if c == '"':
                if i + 1 < len(s) and s[i + 1] == '"':
                    i += 1
                else:
                    inq = False
        elif c == '"':
            inq = True
        elif c == '/' and i + 1 < len(s) and s[i + 1] == '/':
            j = s.find("\n", i)
            i = len(s) if j < 0 else j
            continue
        elif c == '/' and i + 1 < len(s) and s[i + 1] == '*':
            j = s.find("*/", i + 2)
            if j < 0:
                return -1
            i = j + 2
            continue
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def guard_calls(m, fname, arg):
    """Append `, arg` to every fname(...) call lacking a MissingField argument.

    Returns (new_m, count, ok). ok=False means a call could not be scanned and
    the caller should skip the whole query rather than guess.
    """
    out = m
    i = 0
    n = 0
    while True:
        j = out.find(fname + "(", i)
        if j < 0:
            break
        op = j + len(fname)
        end = _scan_call(out, op)
        if end < 0:
            return out, n, False
        if "MissingField." in out[op:end]:
            i = end
            continue
        out = out[:end - 1] + ", " + arg + out[end - 1:]
        n += 1
        i = end + len(arg) + 2
    return out, n, True


def append_lock(m, expr, step='#"Schema Locked"'):
    """Insert a terminal lock step before the OUTER `in` clause. Returns (new_m, ok).

    Two hazards this exists to handle:
      * the body is de-indented, so the outer let/in sit at column 0 while a
        nested `let ... in` inside Table.AddColumn is indented -- anchor on the
        LAST zero-indent `in`;
      * the step separator must land on the last line carrying CODE, because a
        trailing `// comment` would swallow the comma and silently fuse two
        let-bindings into invalid M.
    """
    ins = list(re.finditer(r"(?m)^in[ \t]*$", m))
    if not ins:
        return m, False
    last = ins[-1]
    tail = m[last.end():].strip()
    if not re.fullmatch(r'(?:#"[^"]+"|[A-Za-z_][A-Za-z0-9_\.]*)', tail):
        return m, False

    body = m[:last.start()].rstrip("\r\n")
    if "/*" in body:
        return m, False
    lines = body.split("\n")

    i = len(lines) - 1
    while i >= 0:
        code, _ = split_line_comment(lines[i])
        if code.strip():
            break
        i -= 1
    if i < 0:
        return m, False

    code, comment = split_line_comment(lines[i])
    if not code.rstrip().endswith(","):
        pad = " " if comment else ""
        lines[i] = code.rstrip() + "," + pad + comment
    return ("\n".join(lines) + "\n    " + step + " = " + expr.replace("<LAST>", tail)
            + "\nin\n    " + step), True
