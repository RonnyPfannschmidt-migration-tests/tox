"""
On Windows we use overlapped mechanism, borrowing it from asyncio (but without the event loop).
"""
from asyncio.windows_utils import BUFSIZE  # pragma: win32 cover
from typing import Callable  # pragma: win32 cover

import _overlapped  # type: ignore[import]  # pragma: win32 cover

from .read_via_thread import ReadViaThread  # pragma: win32 cover


class ReadViaThreadWindows(ReadViaThread):  # pragma: win32 cover
    def __init__(self, file_no: int, handler: Callable[[bytes], None], name: str, on_exit_drain: bool) -> None:
        super().__init__(file_no, handler, name, on_exit_drain)
        self.closed = False

    def _read_stream(self) -> None:
        ov = None
        while not self.stop.is_set():
            if ov is None:
                ov = _overlapped.Overlapped(0)
                try:
                    ov.ReadFile(self.file_no, 1)  # type: ignore[attr-defined]
                except BrokenPipeError:
                    self.closed = True
                    return
            data = ov.getresult(10)  # wait for 10ms
            ov = None
            self.handler(data)

    def _drain_stream(self) -> bytes:
        length, result = 1 if self.closed else 1, b""
        while length:
            ov = _overlapped.Overlapped(0)
            try:
                ov.ReadFile(self.file_no, BUFSIZE)  # type: ignore[attr-defined]
                data = ov.getresult()
            except OSError:
                length = 0
            else:
                result += data
                length = len(data)
        return result
