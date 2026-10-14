"""Locate the Power BI Desktop libraries these tools borrow.

Two of them do the work nothing else can:

  Microsoft.MashupEngine.dll        the M compiler and parser Power BI itself
                                    uses -- the only thing that actually knows
                                    M's grammar
  Microsoft.PowerBI.AdomdClient.dll the client that can query a running
                                    Desktop instance's DMVs from a shell

Neither is redistributable, so setup copies them out of the local install
rather than the repo carrying them.

The path is NOT hardcoded. A default MSI install lands in Program Files, but
the Store build lives under WindowsApps with a versioned folder name, and an
enterprise install can be anywhere. setup.ps1 records what it found in
pbi_paths.json; this resolves that first and probes as a fallback, so the tools
work even if setup was never run.
"""
import os
import re
import json
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "pbi_paths.json")

CANDIDATES = [
    r"C:\Program Files\Microsoft Power BI Desktop\bin",
    r"C:\Program Files (x86)\Microsoft Power BI Desktop\bin",
    r"C:\Program Files\WindowsApps\Microsoft.MicrosoftPowerBIDesktop_*\bin",
]


def _from_config(key):
    try:
        with open(CONFIG, encoding="utf-8") as fh:
            v = json.load(fh).get(key)
        if v and os.path.exists(v):
            return v
    except Exception:
        pass
    return None


def bin_dir():
    v = _from_config("bin")
    if v:
        return v
    for pat in CANDIDATES:
        for d in sorted(glob.glob(pat), reverse=True):
            if os.path.isdir(d):
                return d
    return None


def dll(name):
    """Full path to a Desktop library, or None."""
    v = _from_config(name)
    if v:
        return v
    b = bin_dir()
    if not b:
        return None
    p = os.path.join(b, name)
    return p if os.path.exists(p) else None


def mashup_engine():
    return dll("Microsoft.MashupEngine.dll")


def adomd_client():
    return dll("Microsoft.PowerBI.AdomdClient.dll")


def require(what, path):
    if not path:
        raise SystemExit(
            "%s not found. Run setup.ps1, or install Power BI Desktop.\n"
            "Looked in: %s" % (what, ", ".join(CANDIDATES)))
    return path
