"""Extract literal Table.RenameColumns pairs, following chains.

Yields {final_target: original_source} so the drift canary can probe the name
that actually has to exist in the share. A rename target never exists upstream,
so probing it would blind the canary to its source disappearing.
"""
import re
from lockm import _scan_call

PAIR = re.compile(r'\{\s*"((?:[^"]|"")*)"\s*,\s*"((?:[^"]|"")*)"\s*\}')


def extract_renames(m):
    chain = {}
    i = 0
    while True:
        j = m.find("Table.RenameColumns(", i)
        if j < 0:
            break
        op = j + len("Table.RenameColumns")
        end = _scan_call(m, op)
        if end < 0:
            break
        for old, new in PAIR.findall(m[op:end]):
            old, new = old.replace('""', '"'), new.replace('""', '"')
            if old == new:
                continue
            chain[new] = chain.pop(old, old)
        i = end
    return chain
