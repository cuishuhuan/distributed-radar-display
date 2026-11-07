"""Windows ZMQ-to-web bridge for the distributed radar display.

Run on the Windows host that can access radar publishers. The existing browser
page can be served locally with --web-root; no Qt process is required.
"""

from __future__ import annotations

import argparse
import json
import logging
import threading
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from protocol import ProtocolError, inspect_message


LOG = logging.getLogger("radar_bridge")


class MessageStore:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.received = 0
        self.rejected = 0
        self.latest = {}
        self.recent = deque(maxlen=30)
        self.last_error = None

    def accept(self, source: str, message: bytes) -> None:
        try:
            parsed = inspect_message(message)
        except ProtocolError as exc:
            with self.lock:
                self.rejected += 1
                self.last_error = f"{source}: {exc}"
            LOG.warning("拒绝 %s 的消息：%s", source, exc)
            return
        record = {
            "source": source,
            "receivedUtc": datetime.now(timezone.utc).isoformat(),
            **parsed,
        }
        with self.lock:
            self.received += 1
            self.latest[parsed["kind"]] = record
            self.recent.appendleft(record)
        LOG.info("%s: %s (%d B)", source, parsed["kind"], len(message))

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "mode": "live" if self.received else "waiting",
                "updatedUtc": self.recent[0]["receivedUtc"] if self.recent else None,
                "receivedMessages": self.received,
                "rejectedMessages": self.rejected,
                "lastError": self.last_error,
                "latest": dict(self.latest),
                "recent": list(self.recent),
                # Real vessel data is intentionally empty until verified decoders exist.
                "tracks": [],
                "points": [],
            }


def receive_loop(sources: list[dict], store: MessageStore, stop: threading.Event) -> None:
    try:
        import zmq
    except ImportError as exc:
        raise RuntimeError("请先安装 pyzmq：python -m pip install pyzmq") from exc

    context = zmq.Context()
    poller = zmq.Poller()
    sockets = {}
    try:
        for source in sources:
            endpoint = source["endpoint"]
            socket = context.socket(zmq.SUB)
            socket.setsockopt(zmq.RCVHWM, 100)
            socket.setsockopt(zmq.MAXMSGSIZE, 64 * 1024 * 1024)
            topic = source.get("topic", "").encode("utf-8")
            socket.setsockopt(zmq.SUBSCRIBE, topic)
            if source.get("bind", False):
                socket.bind(endpoint)
            else:
                socket.connect(endpoint)
            poller.register(socket, zmq.POLLIN)
            sockets[socket] = source.get("name", endpoint)
            LOG.info("订阅 %s：%s", sockets[socket], endpoint)
        while not stop.is_set():
            for socket in dict(poller.poll(200)):
                frames = socket.recv_multipart()
                if frames:
                    # Existing sender emits one binary frame. For multipart senders,
                    # the final frame is the protocol payload; confirm with samples.
                    store.accept(sockets[socket], frames[-1])
    finally:
        for socket in sockets:
            socket.close(linger=0)
        context.term()


def make_handler(store: MessageStore, web_root: Path | None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path in ("/api/state", "/api/health"):
                self.send_json(store.snapshot())
                return
            if path == "/":
                self.send_file(web_root / "ui-index.html" if web_root else None)
                return
            if path.startswith("/assets/") and web_root:
                name = path.removeprefix("/assets/")
                if "/" not in name and "\\" not in name and name not in (".", ".."):
                    self.send_file(web_root / name)
                    return
            self.send_error(404)

        def send_json(self, value: dict) -> None:
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_file(self, path: Path | None) -> None:
            if path is None or not path.is_file():
                self.send_error(404, "请通过 --web-root 指定网页文件目录")
                return
            body = path.read_bytes()
            import mimetypes

            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            LOG.info("HTTP %s", format % args)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Windows 雷达 ZMQ 网页接入框架")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("settings.json"))
    parser.add_argument("--web-root", type=Path, help="含 ui-index.html 和模型/图片资源的目录")
    parser.add_argument("--inspect", type=Path, help="离线检查一份 ZMQ 消息文件后退出")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.inspect:
        result = inspect_message(args.inspect.read_bytes())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    config = json.loads(args.config.read_text(encoding="utf-8")) if args.config.exists() else {}
    host = config.get("host", "127.0.0.1")
    port = int(config.get("port", 8080))
    sources = config.get("sources", [])
    web_root = args.web_root or (Path(config["web_root"]) if config.get("web_root") else None)
    if web_root:
        web_root = web_root.resolve()
        if not (web_root / "ui-index.html").is_file():
            parser.error(f"网页目录缺少 ui-index.html：{web_root}")

    store = MessageStore()
    stop = threading.Event()
    if sources:
        thread = threading.Thread(target=receive_loop, args=(sources, store, stop), daemon=True)
        thread.start()
    else:
        LOG.warning("没有配置 ZMQ 数据源，服务处于等待状态")
    server = ThreadingHTTPServer((host, port), make_handler(store, web_root))
    LOG.info("网页和接口：http://%s:%d/", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
