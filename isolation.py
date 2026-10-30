"""Runtime isolation adapter for MS VPS.

Docker is preferred. On hosts such as Railway where a Docker daemon is not
available, the adapter exposes a clearly-labelled resource-limited fallback.
The fallback is compatibility/development support, not a security boundary.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess


def _docker_available() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    try:
        return subprocess.run(
            [docker, "info"], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=2, check=False
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def isolation_mode() -> str:
    return "docker" if _docker_available() else "sandbox"


def clean_child_env() -> dict[str, str]:
    env = os.environ.copy()
    # Do not leak the panel's Python path or service-specific preload hooks.
    for key in ("PYTHONPATH", "PYTHONHOME", "LD_PRELOAD", "DOCKER_HOST"):
        env.pop(key, None)
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def build_run_command(username, filepath, sandbox_script, *, is_master=False,
                      fallback_cmd=None):
    """Return (shell command, mode).

    Docker mode is intentionally conservative and only uses a read/write
    bind mount for the project directory. The caller supplies the normal
    command as fallback for hosts without Docker.
    """
    mode = isolation_mode()
    if mode == "docker":
        project_dir = os.path.dirname(os.path.realpath(filepath))
        image = os.environ.get("MS_VPS_SANDBOX_IMAGE", "python:3.11-slim")
        command = fallback_cmd or ""
        return (
            "docker run --rm --network none --read-only "
            "--cap-drop ALL --security-opt no-new-privileges "
            "--pids-limit 128 --memory 512m --cpus 1 "
            f"-v {shlex.quote(project_dir)}:/workspace:rw "
            f"-w /workspace {shlex.quote(image)} sh -lc {shlex.quote(command)}",
            "docker",
        )

    # Compatibility mode: the parent process still applies the project's
    # static checks, process-group handling and dependency allowlists.
    # ulimit prevents common runaway-process/resource cases.
    if not fallback_cmd:
        return None, "sandbox"
    limited = (
        "ulimit -t ${MS_VPS_CPU_SECONDS:-300} 2>/dev/null || true; "
        "ulimit -v ${MS_VPS_MEMORY_KB:-1048576} 2>/dev/null || true; "
        "ulimit -n 256 2>/dev/null || true; "
        f"exec {fallback_cmd}"
    )
    return f"sh -lc {shlex.quote(limited)}", "sandbox"


def build_shell_command(username, cwd, command):
    return command


def stop_container(username, filepath):
    return None
