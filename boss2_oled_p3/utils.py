import subprocess

SUBPROCESS_TIMEOUT = 30


def shell_cmd(cmd, timeout=SUBPROCESS_TIMEOUT):
    """Run a shell command and return the stdout."""
    out = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    stdout, stderr = out.communicate(timeout=timeout)
    return stdout, stderr
