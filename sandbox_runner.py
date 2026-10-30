#!/usr/bin/env python3
"""Run one user script with a filesystem boundary at the Python audit layer.
This is defense-in-depth; the hosting container should still be the primary boundary.
"""
import builtins
import os
import runpy
import sys

ROOT = os.path.realpath(os.path.abspath(sys.argv[1]))
USERS_ROOT = os.path.realpath(os.path.dirname(ROOT))
SCRIPT = os.path.realpath(os.path.abspath(sys.argv[2]))
if not os.path.isdir(ROOT) or not SCRIPT.startswith(ROOT + os.sep):
    raise SystemExit("sandbox: invalid user path")

_orig_open = builtins.open
_orig_os_open = os.open
_orig_listdir = os.listdir
_orig_scandir = os.scandir

def _inside(path):
    if isinstance(path, int):
        return True
    try:
        real = os.path.realpath(os.path.abspath(os.fspath(path)))
        # Python libraries may be read, but sibling user folders are never visible.
        if real == ROOT or real.startswith(ROOT + os.sep):
            return True
        return not real.startswith(USERS_ROOT + os.sep)
    except Exception:
        return False

def _check(path):
    if not _inside(path):
        raise PermissionError("sandbox: access outside the user folder is denied")

def safe_open(file, *args, **kwargs):
    _check(file)
    return _orig_open(file, *args, **kwargs)

def safe_os_open(file, *args, **kwargs):
    _check(file)
    return _orig_os_open(file, *args, **kwargs)

def safe_listdir(path= '.'):
    _check(path)
    return _orig_listdir(path)

def safe_scandir(path='.'):
    _check(path)
    return _orig_scandir(path)


builtins.open = safe_open
os.open = safe_os_open
os.listdir = safe_listdir
os.scandir = safe_scandir
os.chdir(ROOT)
os.environ['HOME'] = ROOT
os.environ['TMPDIR'] = ROOT

# Block subprocesses and dynamic execution from escaping the same boundary.
def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.exec', 'os.spawn'):
        raise PermissionError('sandbox: child processes are disabled')
    if event in ('open', 'os.open') and args:
        _check(args[0])

sys.addaudithook(audit)
runpy.run_path(SCRIPT, run_name='__main__')
