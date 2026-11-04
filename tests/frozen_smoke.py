"""Opt-in Linux binary startup smoke in an isolated data/working directory.

Checks 15 seconds of startup and stderr, then terminates only the process
group created by this test. It does not test hardware or camera connectivity.
"""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import psutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", action="store_true", help="Test the Windows executable using the project Wine prefix")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    work = root / ".work" / "tmp"
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="frozen-", dir=work) as directory:
        environment = dict(os.environ, NETTOOLS_DATA_DIR=str(Path(directory) / "data"))
        command = [str(root / "dist" / "NetToolsPro.bin")]
        if args.windows:
            environment.update(
                WINEPREFIX=str(root / "build" / "windows-wine"), WINEARCH="win64", WINEDEBUG="-all",
                WINEDLLOVERRIDES="winemenubuilder.exe,mscoree,mshtml=d",
                XDG_CONFIG_HOME=str(root / "build/windows-xdg/config"),
                XDG_CACHE_HOME=str(root / "build/windows-xdg/cache"),
                XDG_DATA_HOME=str(root / "build/windows-xdg/data"),
                NETTOOLS_DATA_DIR="N:\\" + str(Path(directory).relative_to(root) / "data").replace("/", "\\"),
            )
            command = ["wine", str(root / "dist" / "NetToolsPro.exe")]
        # Wine services can retain inherited pipes after the app exits. Files
        # keep those services from blocking communicate() during cleanup.
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen(command, cwd=directory, env=environment, start_new_session=True,
                                       stdout=stdout, stderr=stderr)
            survived = False
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                survived = True
            finally:
                if args.windows:
                    # Wine may detach the onefile child from the launcher.
                    # Match only this test's unique cwd and executable name.
                    owned = []
                    for candidate in psutil.process_iter(["name"]):
                        try:
                            if (candidate.info["name"].lower() == "nettoolspro.exe"
                                    and candidate.cwd() == directory):
                                owned.append(candidate)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    for candidate in owned:
                        candidate.terminate()
                    _, alive = psutil.wait_procs(owned, timeout=2)
                    for candidate in alive:
                        candidate.kill()
                    _, alive = psutil.wait_procs(alive, timeout=3)
                    assert not alive, "A Windows smoke process survived cleanup"
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3)
            stderr.seek(0)
            error = stderr.read().decode("utf-8", errors="replace")
        assert survived, f"Binary exited during startup (code {process.returncode})"
        assert not error.strip(), f"Binary produced startup stderr ({len(error)} characters); inspect locally"
        print("PASS: packaged binary ran for 15 seconds from an isolated working directory; no stderr")


if __name__ == "__main__":
    main()
