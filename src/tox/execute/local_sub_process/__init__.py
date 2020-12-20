"""Execute that runs on local file system via subprocess-es"""
import logging
import os
import shutil
import sys
from subprocess import PIPE, TimeoutExpired
from types import TracebackType
from typing import TYPE_CHECKING, Generator, List, Optional, Sequence, Tuple, Type

from tox.execute.stream import SyncWrite

from ..api import SIGINT, Execute, ExecuteInstance, ExecuteStatus, Outcome
from ..request import ExecuteRequest, StdinSource
from .read_via_thread import WAIT_GENERAL

if sys.platform == "win32":  # pragma: win32 cover
    # needs stdin/stdout handlers backed by overlapped IO
    if TYPE_CHECKING:  # the typeshed libraries don't contain this, so replace it with normal one
        from subprocess import Popen
    else:
        from asyncio.windows_utils import Popen
    from subprocess import CREATE_NEW_PROCESS_GROUP

    from .read_via_thread_windows import ReadViaThreadWindows as ReadViaThread

    CREATION_FLAGS = CREATE_NEW_PROCESS_GROUP  # a custom flag needed for Windows signal send ability (CTRL+C)

else:  # pragma: win32 no cover
    from subprocess import Popen

    from .read_via_thread_unix import ReadViaThreadUnix as ReadViaThread

    CREATION_FLAGS = 0


WAIT_INTERRUPT = 0.3
WAIT_TERMINATE = 0.2


class LocalSubProcessExecutor(Execute):
    def build_instance(self, request: ExecuteRequest, out: SyncWrite, err: SyncWrite) -> ExecuteInstance:
        return LocalSubProcessExecuteInstance(request, out, err)


class LocalSubprocessExecuteStatus(ExecuteStatus):
    def __init__(self, out: SyncWrite, err: SyncWrite, process: "Popen[bytes]"):
        self._process: "Popen[bytes]" = process
        super().__init__(out, err)

    @property
    def exit_code(self) -> Optional[int]:
        return self._process.returncode

    def wait(self, timeout: Optional[float] = None) -> None:
        # note poll in general might deadlock if output large, but we drain in background threads so not an issue here
        try:
            self._process.wait(timeout=WAIT_GENERAL if timeout is None else timeout)
        except TimeoutExpired:
            pass

    def write_stdin(self, content: str) -> None:
        stdin = self._process.stdin
        if stdin is not None:
            bytes_content = content.encode()
            if sys.platform == "win32":  # pragma: win32 cover
                # on Windows we have a PipeHandle object here rather than a file stream
                import _overlapped  # type: ignore[import]

                ov = _overlapped.Overlapped(0)
                ov.WriteFile(stdin.handle, bytes_content)  # type: ignore[attr-defined]
                result = ov.getresult(10)  # wait up to 10ms to perform the operation
                if result != len(bytes_content):
                    raise RuntimeError(f"failed to write to {stdin!r}")
            else:
                stdin.write(bytes_content)
                stdin.flush()

    def close_stdin(self) -> None:
        stdin = self._process.stdin
        if stdin is not None:
            stdin.close()


class LocalSubprocessExecuteFailedStatus(ExecuteStatus):
    def __init__(self, out: SyncWrite, err: SyncWrite, exit_code: Optional[int]) -> None:
        super().__init__(out, err)
        self._exit_code = exit_code

    @property
    def exit_code(self) -> Optional[int]:
        return self._exit_code

    def wait(self, timeout: Optional[float] = None) -> None:
        """already dead no need to wait"""

    def write_stdin(self, content: str) -> None:
        """cannot write"""

    def close_stdin(self) -> None:
        """never opened, nothing to close"""


class LocalSubProcessExecuteInstance(ExecuteInstance):
    def __init__(
        self,
        request: ExecuteRequest,
        out: SyncWrite,
        err: SyncWrite,
        on_exit_drain: bool = True,
    ) -> None:
        super().__init__(request, out, err)
        self.process: Optional[Popen[bytes]] = None
        self._cmd: Optional[List[str]] = None
        self._read_stderr: Optional[ReadViaThread] = None
        self._read_stdout: Optional[ReadViaThread] = None
        self._on_exit_drain = on_exit_drain

    @property
    def cmd(self) -> Sequence[str]:
        if self._cmd is None:
            executable = shutil.which(self.request.cmd[0], path=self.request.env["PATH"])
            if executable is None:
                cmd = self.request.cmd  # if failed to find leave as it is
            else:
                # else use expanded format
                cmd = [executable, *self.request.cmd[1:]]
            self._cmd = cmd
        return self._cmd

    def __enter__(self) -> ExecuteStatus:
        stdout, stderr = self.get_stream_file_no("stdout"), self.get_stream_file_no("stderr")
        try:
            self.process = process = Popen(
                self.cmd,
                stdout=next(stdout),
                stderr=next(stderr),
                stdin=None if self.request.stdin is StdinSource.USER else PIPE,
                cwd=str(self.request.cwd),
                env=self.request.env,
                creationflags=CREATION_FLAGS,
            )
        except OSError as exception:
            return LocalSubprocessExecuteFailedStatus(self._out, self._err, exception.errno)

        status = LocalSubprocessExecuteStatus(self._out, self._err, process)
        if self.request.stdin is StdinSource.OFF:
            status.close_stdin()
        pid = self.process.pid
        self._read_stderr = ReadViaThread(
            stderr.send(process), self.err_handler, name=f"err-{pid}", on_exit_drain=self._on_exit_drain
        )
        self._read_stderr.__enter__()
        self._read_stdout = ReadViaThread(
            stdout.send(process), self.out_handler, name=f"out-{pid}", on_exit_drain=self._on_exit_drain
        )
        self._read_stdout.__enter__()

        if sys.platform == "win32":  # pragma: win32 cover
            process.stderr.read = self._read_stderr._drain_stream  # type: ignore[assignment,union-attr]
            process.stdout.read = self._read_stdout._drain_stream  # type: ignore[assignment,union-attr]
        # wait it out with interruptions to allow KeyboardInterrupt on Windows
        return status

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        if self._read_stderr is not None:
            self._read_stderr.__exit__(exc_type, exc_val, exc_tb)
        if self._read_stdout is not None:
            self._read_stdout.__exit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def get_stream_file_no(key: str) -> Generator[int, "Popen[bytes]", None]:
        if sys.platform != "win32" and getattr(sys, key).isatty():  # pragma: win32 no cover
            # on UNIX if tty is set let's forward it via a pseudo terminal
            # this allows processes running to access the host terminals traits
            import pty

            main, child = pty.openpty()
            yield child
            os.close(child)
            yield main
        else:
            process = yield PIPE
            stream = getattr(process, key)
            if sys.platform == "win32":  # pragma: win32 cover
                yield stream.handle
            else:
                yield stream.name

    def interrupt(self) -> int:
        if self.process is not None:
            # A three level stop mechanism for children - INT -> TERM -> KILL
            # communicate will wait for the app to stop, and then drain the standard streams and close them
            proc = self.process
            logging.error("got KeyboardInterrupt signal")
            msg = f"from {os.getpid()} {{}} pid {proc.pid}"
            if proc.poll() is None:  # still alive, first INT
                logging.warning("KeyboardInterrupt %s", msg.format("SIGINT"))
                proc.send_signal(SIGINT)
                try:
                    out, err = proc.communicate(timeout=WAIT_INTERRUPT)
                except TimeoutExpired:  # if INT times out TERM
                    logging.warning("KeyboardInterrupt %s", msg.format("SIGTERM"))
                    proc.terminate()
                    try:
                        out, err = proc.communicate(timeout=WAIT_INTERRUPT)
                    except TimeoutExpired:  # if TERM times out KILL
                        logging.info("KeyboardInterrupt %s", msg.format("SIGKILL"))
                        proc.kill()
                        out, err = proc.communicate()
            else:  # pragma: no cover # difficult to test, process must die just as it's being interrupted
                try:
                    out, err = proc.communicate()  # just drain
                except ValueError:  # if already drained via another communicate
                    out, err = b"", b""
            self.out_handler(out)
            self.err_handler(err)
            return int(self.process.returncode)
        return Outcome.OK  # pragma: no cover

    def set_out_err(self, out: SyncWrite, err: SyncWrite) -> Tuple[SyncWrite, SyncWrite]:
        prev = self._out, self._err
        if self._read_stdout is not None:
            self._read_stdout.handler = out.handler
        if self._read_stderr is not None:
            self._read_stderr.handler = err.handler
        return prev
