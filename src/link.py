"""One peer per table. All UI callbacks are dispatched on Tk's thread."""
import json
import queue
import socket
import threading

PORT = 41667


class Link:
    def __init__(self):
        self.events = queue.Queue()
        self.outbox = queue.Queue()
        self.closed = threading.Event()
        self.listener = self.peer = None

    def start(self, address=None):
        threading.Thread(target=self._run, args=(address,), daemon=True).start()

    def _run(self, address):
        try:
            if address is None:
                with socket.socket() as server:
                    self.listener = server
                    server.bind(("", PORT))
                    server.listen(1)
                    server.settimeout(.4)
                    self.events.put(("listening", None))
                    while not self.closed.is_set():
                        try:
                            self.peer, _ = server.accept()
                            break
                        except socket.timeout:
                            continue
            else:
                self.peer = socket.create_connection((address, PORT), timeout=5)
            if self.closed.is_set():
                return
            with self.peer as peer:
                peer.settimeout(5)
                peer.sendall(b"GAMBIT-67/10\n")
                with peer.makefile("rb") as reader:
                    if reader.readline(32) != b"GAMBIT-67/10\n":
                        raise ValueError("Несовместимая версия игры.")
                    peer.settimeout(None)
                    threading.Thread(target=self._write, daemon=True).start()
                    self.events.put(("connected", None))
                    while not self.closed.is_set():
                        line = reader.readline(8193)
                        if not line:
                            raise ConnectionError("Второй игрок отключился.")
                        if len(line) > 8192:
                            raise ValueError("Слишком большое сообщение.")
                        msg = json.loads(line)
                        if not isinstance(msg, dict):
                            raise ValueError("Некорректное сообщение.")
                        self.events.put(("message", msg))
        except (OSError, ValueError) as exc:
            if not self.closed.is_set():
                self.events.put(("error", str(exc)))
        finally:
            self.close()

    def _write(self):
        while not self.closed.is_set():
            msg = self.outbox.get()
            if msg is None:
                return
            try:
                self.peer.sendall(json.dumps(msg).encode() + b"\n")
            except OSError:
                self.close()
                self.events.put(("error", "Соединение потеряно."))
                return

    def close(self):
        self.closed.set()
        self.outbox.put(None)
        for sock in (self.peer, self.listener):
            if sock:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                sock.close()
