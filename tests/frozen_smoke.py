"""Opt-in Linux binary startup smoke in an isolated data/working directory.

Checks 15 seconds of startup and stderr, then terminates only the process
group created by this test. It does not test hardware or camera connectivity.
"""
import os
from pathlib import Path
import signal
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    work = root / ".test-work"
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="frozen-", dir=work) as directory:
        environment = dict(os.environ, NETTOOLS_DATA_DIR=str(Path(directory) / "data"))
        process = subprocess.Popen([str(root / "dist" / "NetToolsPro.bin")],
                                   cwd=directory, env=environment, start_new_session=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        survived = False
        try:
            process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            survived = True
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            try:
                output, error = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                output, error = process.communicate(timeout=5)
        assert survived, f"Binary exited during startup (code {process.returncode})"
        assert not error.strip(), f"Binary produced startup stderr ({len(error)} characters); inspect locally"
        print("PASS: packaged binary ran for 15 seconds from an isolated working directory; no stderr")


if __name__ == "__main__":
    main()
