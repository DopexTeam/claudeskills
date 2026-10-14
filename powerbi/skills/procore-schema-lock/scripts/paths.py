"""Where per-project state lives.

Deliberately OUTSIDE the skill folder. The skill is meant to be copied into a
shared repository, and everything these tools generate is client data: calcdep
captures carry a model's whole dependency graph, required/derived carry column
names, and backup carries entire semantic models -- including the share tokens
that appear in expressions.tmdl. A .gitignore protects a git push; it does not
protect someone zipping the folder.

So the default is ~/.procore-schema-lock, and no client bytes ever sit inside
the skill directory. Override with PROCORE_LOCK_DATA to put it somewhere else,
such as alongside a private repo.

    calcdep/   <project>.csv   INFO.CALCDEPENDENCY, captured from a live model
    required/  <project>.json  columns the report actually consumes
    derived/   <project>.json  columns the M creates, so never in the share
    backup/    pre-apply copies of every file a tool rewrites
"""
import os

ENV = "PROCORE_LOCK_DATA"


def data_root():
    r = os.environ.get(ENV)
    if not r:
        r = os.path.join(os.path.expanduser("~"), ".procore-schema-lock")
    return r


def data_dir(kind, create=True):
    """kind: calcdep | required | derived | backup"""
    d = os.path.join(data_root(), kind)
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def data_file(kind, name, create=True):
    return os.path.join(data_dir(kind, create), name)
