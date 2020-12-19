"""
Abstract base API for executing commands within tox environments.
"""
import logging
import signal
import sys
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from types import TracebackType
from typing import Callable, Iterator, NoReturn, Optional, Sequence, Tuple, Type

from colorama import Fore

from tox.report import OutErr

from .request import ExecuteRequest, StdinSource
from .stream import SyncWrite

ContentHandler = Callable[[bytes], None]
Executor = Callable[[ExecuteRequest, ContentHandler, ContentHandler], int]
if sys.platform == "win32":  # pragma: win32 cover
    SIGINT = signal.CTRL_C_EVENT
else:
    SIGINT = signal.SIGINT

LOGGER = logging.getLogger(__name__)


class ExecuteStatus(ABC):
    def __init__(self, out: SyncWrite, err: SyncWrite) -> None:
        self.outcome: Optional[Outcome] = None
        self._out = out
        self._err = err

    @property
    @abstractmethod
    def exit_code(self) -> Optional[int]:
        raise NotImplementedError

    @abstractmethod
    def wait(self, timeout: Optional[float] = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def write_stdin(self, content: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def close_stdin(self) -> None:
        raise NotImplementedError

    def set_out_err(self, out: SyncWrite, err: SyncWrite) -> Tuple[SyncWrite, SyncWrite]:
        res = self._out, self._err
        self._out, self._err = out, err
        return res

    @property
    def out(self) -> bytearray:
        return self._out.content

    @property
    def err(self) -> bytearray:
        return self._err.content


class Execute(ABC):
    """Abstract API for execution of a tox environment"""

    def __init__(self, colored: bool) -> None:
        self._colored = colored

    @contextmanager
    def call(self, request: ExecuteRequest, show: bool, out_err: OutErr) -> Iterator[ExecuteStatus]:
        start = time.monotonic()
        interrupt = None
        try:
            # collector is what forwards the content from the file streams to the standard streams
            out = out_err[0].buffer
            with SyncWrite(out.name, out if show else None) as out_sync:
                err = out_err[1].buffer
                with SyncWrite(err.name, err if show else None, Fore.RED if self._colored else None) as err_sync:
                    instance = self.build_instance(request, out_sync, err_sync)
                    try:
                        with instance as status:
                            yield status
                        exit_code = status.exit_code
                    except KeyboardInterrupt as exception:
                        interrupt = exception
                        while True:
                            try:
                                is_main = threading.current_thread() == threading.main_thread()
                                if is_main:
                                    # disable further interrupts until we finish this, main thread only
                                    if sys.platform != "win32":  # pragma: win32 cover
                                        signal.signal(SIGINT, signal.SIG_IGN)
                            except KeyboardInterrupt:  # pragma: no cover
                                continue  # pragma: no cover
                            else:
                                try:
                                    exit_code = instance.interrupt()
                                    break
                                finally:
                                    # restore signal handler on main thread
                                    if is_main and sys.platform != "win32":  # pragma: no cover
                                        signal.signal(SIGINT, signal.default_int_handler)
        finally:
            end = time.monotonic()
        status.outcome = Outcome(request, show, exit_code, out_sync.text, err_sync.text, start, end, instance.cmd)
        if interrupt is not None:
            raise ToxKeyboardInterrupt(status.outcome, interrupt)

    @abstractmethod
    def build_instance(self, request: ExecuteRequest, out: SyncWrite, err: SyncWrite) -> "ExecuteInstance":
        raise NotImplementedError


class ExecuteInstance(ABC):
    """An instance of a command execution"""

    def __init__(self, request: ExecuteRequest, out: SyncWrite, err: SyncWrite) -> None:
        self.request = request
        self._out = out
        self._err = err

    @property
    def out_handler(self) -> ContentHandler:
        return self._out.handler

    @property
    def err_handler(self) -> ContentHandler:
        return self._err.handler

    @abstractmethod
    def __enter__(self) -> ExecuteStatus:
        raise NotImplementedError

    @abstractmethod
    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def interrupt(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def cmd(self) -> Sequence[str]:
        raise NotImplementedError


class Outcome:
    """Result of a command execution"""

    OK = 0

    def __init__(
        self,
        request: ExecuteRequest,
        show_on_standard: bool,
        exit_code: Optional[int],
        out: str,
        err: str,
        start: float,
        end: float,
        cmd: Sequence[str],
    ):
        self.request = request
        self.show_on_standard = show_on_standard
        self.exit_code = exit_code
        self.out = out
        self.err = err
        self.start = start
        self.end = end
        self.cmd = cmd

    def __bool__(self) -> bool:
        return self.exit_code == self.OK

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}: exit {self.exit_code} in {self.elapsed:.2f} seconds"
            f" for {self.request.shell_cmd}"
        )

    def assert_success(self) -> None:
        if self.exit_code is not None and self.exit_code != self.OK:
            self._assert_fail()
        self.log_run_done(logging.INFO)

    def _assert_fail(self) -> NoReturn:
        if self.show_on_standard is False:
            if self.out:
                print(self.out, file=sys.stdout)
            if self.err:
                print(Fore.RED, file=sys.stderr, end="")
                print(self.err, file=sys.stderr, end="")
                print(Fore.RESET, file=sys.stderr)
        self.log_run_done(logging.CRITICAL)
        raise SystemExit(self.exit_code)

    def log_run_done(self, lvl: int) -> None:
        req = self.request
        LOGGER.log(lvl, "exit %s (%.2f seconds) %s> %s", self.exit_code, self.elapsed, req.cwd, req.shell_cmd)

    @property
    def elapsed(self) -> float:
        return self.end - self.start

    def out_err(self) -> Tuple[str, str]:
        return self.out, self.err


class ToxKeyboardInterrupt(KeyboardInterrupt):
    def __init__(self, outcome: Outcome, exc: KeyboardInterrupt):
        self.outcome = outcome
        self.exc = exc


__all__ = (
    "ContentHandler",
    "SIGINT",
    "Outcome",
    "ToxKeyboardInterrupt",
    "Execute",
    "ExecuteInstance",
    "ExecuteStatus",
    "StdinSource",
)
