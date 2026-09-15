#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音乐播放器本地服务（零第三方依赖，仅用 Python 标准库）

作用：
  1. 在本机提供播放器页面  http://127.0.0.1:<端口>/
  2. 代理转发 /api 请求到 https://www.yinyueku.cn/api.php
     —— 该站点 TLS 证书已过期（浏览器/curl 直接访问会握手失败），
        代理转发时跳过证书校验，页面即可正常取数。
     站点证书修复后，也可以不启动本服务、直接双击 HTML 使用。

用法：
  python server.py            # 启动并自动打开浏览器
  python server.py --no-open  # 启动但不打开浏览器
"""

import os
import ssl
import sys
import json
import time
import threading
import webbrowser
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(ROOT, "音乐播放器.html")
UPSTREAM = "https://www.yinyueku.cn/api.php"
PORT_RANGE = range(8964, 8980)          # 依次尝试的本地端口

# 站点证书过期 → 转发时跳过证书校验（仅此上游域名使用）
SSL_CTX = ssl._create_unverified_context()

PROXY_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Referer": "https://www.yinyueku.cn/",
    "Accept": "*/*",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "MusicPlayerProxy/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def handle_error(self, request, client_address):
        # 浏览器关闭页面时强断 keep-alive 连接属正常现象，静默即可
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, BrokenPipeError, TimeoutError)):
            return
        super().handle_error(request, client_address)

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if code != 204:
            self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if body:
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            try:
                with open(HTML_PATH, "rb") as f:
                    body = f.read()
                self._send(200, body, "text/html; charset=utf-8")
            except OSError:
                self._send(500, "找不到 音乐播放器.html".encode("utf-8"),
                           "text/plain; charset=utf-8")
        elif path == "/api":
            self._proxy(parsed.query)
        elif path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
        else:
            self._send(404, b"Not Found", "text/plain; charset=utf-8")

    def _proxy(self, query):
        # 重新编码 query，保证中文等特殊字符正确传递
        qs = urllib.parse.urlencode(urllib.parse.parse_qsl(query, keep_blank_values=True))
        req = urllib.request.Request(UPSTREAM + "?" + qs, headers=PROXY_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
                body = r.read()
                ctype = r.headers.get("Content-Type", "application/json; charset=utf-8")
            self._send(200, body, ctype)
        except Exception as e:  # 网络/超时等
            msg = json.dumps({"error": "上游请求失败: %s" % e}, ensure_ascii=False)
            self._send(502, msg.encode("utf-8"), "application/json; charset=utf-8")


def main():
    no_open = "--no-open" in sys.argv
    srv = None
    for port in PORT_RANGE:
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if srv is None:
        print("无法绑定端口 8964-8979（可能被占用），请释放后重试。", file=sys.stderr)
        sys.exit(1)

    addr = "http://127.0.0.1:%d/" % srv.server_address[1]
    print("=" * 48)
    print("  音乐播放器本地服务已启动")
    print("  地址: %s" % addr)
    print("  关闭本窗口或按 Ctrl+C 即可停止服务")
    print("=" * 48)
    if not no_open:
        threading.Timer(0.8, lambda: webbrowser.open(addr)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
