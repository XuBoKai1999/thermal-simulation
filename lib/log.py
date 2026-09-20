"""Minimal runtime logging shared by simulations and tests."""

from datetime import datetime
from pathlib import Path
from time import perf_counter


class RunLog:
    def __init__(self, every=10, terminal=True, path=None):
        if not isinstance(every, int) or every <= 0:
            raise ValueError("log cadence must be a positive integer")
        self.every = every
        self.terminal = terminal
        self.path = None if path is None else Path(path)
        self.started = perf_counter()

    def _write(self, message):
        line = f"{datetime.now().astimezone().isoformat(timespec='seconds')} | {message}"
        if self.terminal:
            print(line, flush=True)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                print(line, file=handle, flush=True)

    def event(self, kind, message=""):
        self._write(f"{kind}" + (f" | {message}" if message else ""))

    def progress(self, step, total_steps, time_s, dt_s, newton_iterations, label="run"):
        if step == 1 or step == total_steps or step % self.every == 0:
            self._write(
                f"[{label}] step {step}/{total_steps} | t={time_s:g} s | "
                f"dt={dt_s:g} s | Newton={newton_iterations} | "
                f"wall={perf_counter() - self.started:.1f} s"
            )


def self_test():
    from contextlib import redirect_stdout
    from io import StringIO
    from tempfile import TemporaryDirectory

    terminal = StringIO()
    with TemporaryDirectory() as directory, redirect_stdout(terminal):
        path = Path(directory) / "run.log"
        logger = RunLog(every=3, path=path)
        for step in range(1, 8):
            logger.progress(step, 7, step * 0.25, 0.25, 2, "test")
        logger.event("DONE", "ok")
        file_text = path.read_text(encoding="utf-8")
    for text in (terminal.getvalue(), file_text):
        assert "step 1/7 | t=0.25 s | dt=0.25 s" in text
        assert "step 3/7" in text and "step 6/7" in text and "step 7/7" in text
        assert "step 2/7" not in text and "DONE | ok" in text
    print("runtime log self-test: PASS")


if __name__ == "__main__":
    self_test()
