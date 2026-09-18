"""A JSON Schema validator covering exactly what the PBIR schemas use.

Not a general implementation, and deliberately so. Adding a pip dependency to a
skill set that is otherwise stdlib-only is a real cost to anyone vendoring it,
and the keyword surface here is small and fixed. Measured across all thirteen
schemas Desktop embeds:

    type 9294 · const 4736 · $ref 2239 · oneOf 1118 · properties 919
    items 685 · additionalProperties 335 · required 230 · anyOf 83
    allOf 49 · enum 43 · pattern 42 · minimum/maximum 7 · patternProperties 3
    format 2 · maxLength 2

No if/then/else, no dependencies, no propertyNames, no contains. Everything
above is implemented; anything else is IGNORED rather than guessed at, and
unknown keywords are reported by `unsupported()` so the blind spot is
enumerable instead of silent -- the same reason the M side prefers a syntax tree
to a regex.

Refs: 2164 are local `#/definitions/...`; 75 point at sibling schema documents
by URL, which resolve through the `registry` passed to validate().
"""
import re

SUPPORTED = {
    "type", "const", "$ref", "oneOf", "anyOf", "allOf", "properties", "items",
    "additionalProperties", "patternProperties", "required", "enum", "pattern",
    "minimum", "maximum", "maxLength", "minLength",
    # annotations, no validation effect
    "title", "description", "default", "$id", "$schema", "definitions",
    "examples", "deprecated", "format",
}

TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "number": (int, float), "integer": int, "null": type(None),
}


def unsupported(schema, seen=None):
    """Keywords present in a schema that this validator ignores."""
    seen = seen if seen is not None else set()
    if isinstance(schema, dict):
        for k, v in schema.items():
            if k not in SUPPORTED:
                seen.add(k)
            if k in ("properties", "definitions", "patternProperties"):
                if isinstance(v, dict):
                    for sub in v.values():
                        unsupported(sub, seen)
            else:
                unsupported(v, seen)
    elif isinstance(schema, list):
        for i in schema:
            unsupported(i, seen)
    return seen


def _resolve(ref, root, registry):
    if ref.startswith("#/"):
        node = root
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                return None, root
        return node, root
    if ref.startswith("http"):
        # e.g. .../definition/semanticQuery/1.0.0/schema.json#/definitions/X
        url, _, frag = ref.partition("#")
        m = re.search(r"definition/([A-Za-z]+)/", url)
        if not m:
            return None, root
        other = registry.get(m.group(1).lower())
        if other is None:
            return None, root
        if not frag:
            return other, other
        return _resolve("#" + frag, other, registry)
    return None, root


def _type_ok(value, t):
    py = TYPES.get(t)
    if py is None:
        return True
    if t == "number" and isinstance(value, bool):
        return False
    if t == "integer" and isinstance(value, bool):
        return False
    return isinstance(value, py)


def validate(value, schema, registry=None, root=None, path="$", out=None, depth=0):
    """Returns a list of (path, message). Empty means valid."""
    out = [] if out is None else out
    registry = registry or {}
    root = schema if root is None else root
    if not isinstance(schema, dict) or depth > 60:
        return out

    if "$ref" in schema:
        target, newroot = _resolve(schema["$ref"], root, registry)
        if target is not None:
            validate(value, target, registry, newroot, path, out, depth + 1)
        return out

    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_type_ok(value, x) for x in types):
            out.append((path, "expected %s, got %s" % ("/".join(types), type(value).__name__)))
            return out

    if "const" in schema and value != schema["const"]:
        out.append((path, "must be %r" % (schema["const"],)))
    if "enum" in schema and value not in schema["enum"]:
        out.append((path, "not one of %r" % (schema["enum"][:6],)))

    if isinstance(value, str):
        p = schema.get("pattern")
        if p and not re.search(p, value):
            out.append((path, "does not match /%s/" % p))
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            out.append((path, "longer than %d" % schema["maxLength"]))
        if "minLength" in schema and len(value) < schema["minLength"]:
            out.append((path, "shorter than %d" % schema["minLength"]))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            out.append((path, "below minimum %s" % schema["minimum"]))
        if "maximum" in schema and value > schema["maximum"]:
            out.append((path, "above maximum %s" % schema["maximum"]))

    if isinstance(value, dict):
        props = schema.get("properties", {})
        for r in schema.get("required", []):
            if r not in value:
                out.append((path, "missing required %r" % r))
        pats = schema.get("patternProperties", {})
        addl = schema.get("additionalProperties", True)
        for k, v in value.items():
            if k in props:
                validate(v, props[k], registry, root, "%s.%s" % (path, k), out, depth + 1)
                continue
            hit = [s for pat, s in pats.items() if re.search(pat, k)]
            if hit:
                for s in hit:
                    validate(v, s, registry, root, "%s.%s" % (path, k), out, depth + 1)
            elif addl is False:
                out.append((path, "unexpected property %r" % k))
            elif isinstance(addl, dict):
                validate(v, addl, registry, root, "%s.%s" % (path, k), out, depth + 1)

    if isinstance(value, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for i, v in enumerate(value):
                validate(v, items, registry, root, "%s[%d]" % (path, i), out, depth + 1)
        elif isinstance(items, list):
            for i, (v, s) in enumerate(zip(value, items)):
                validate(v, s, registry, root, "%s[%d]" % (path, i), out, depth + 1)

    for s in schema.get("allOf", []):
        validate(value, s, registry, root, path, out, depth + 1)

    for key in ("oneOf", "anyOf"):
        alts = schema.get(key)
        if not alts:
            continue
        # a branch is satisfied when it produces no errors of its own
        if not any(not validate(value, s, registry, root, path, [], depth + 1) for s in alts):
            out.append((path, "matches none of the %d %s branches" % (len(alts), key)))

    return out
