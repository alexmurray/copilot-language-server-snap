#!/usr/bin/env python3
"""Smoke test the copilot-language-server by performing an LSP initialize
handshake over stdio and checking the server reports its capabilities."""

import json
import subprocess
import sys

TIMEOUT = 60


def send(proc, msg):
    body = json.dumps(msg).encode()
    proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    proc.stdin.flush()


def recv(proc):
    headers = {}
    while True:
        line = proc.stdout.readline()
        if not line:
            raise EOFError("server closed stdout")
        line = line.strip()
        if not line:
            break
        key, value = line.decode().split(":", 1)
        headers[key.strip().lower()] = value.strip()
    return json.loads(proc.stdout.read(int(headers["content-length"])))


def main():
    cmd = sys.argv[1:] or ["copilot-language-server"]
    proc = subprocess.Popen(cmd + ["--stdio"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    try:
        send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"processId": None, "rootUri": None,
                               "capabilities": {},
                               "clientInfo": {"name": "smoke-test"}}})
        while True:
            msg = recv(proc)
            if msg.get("id") == 1:
                break
        if "error" in msg:
            sys.exit(f"initialize failed: {msg['error']}")
        result = msg["result"]
        print(json.dumps(result.get("serverInfo"), indent=2))
        assert "capabilities" in result, "no capabilities in response"
        send(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        send(proc, {"jsonrpc": "2.0", "id": 2, "method": "shutdown"})
        send(proc, {"jsonrpc": "2.0", "method": "exit"})
        proc.wait(timeout=TIMEOUT)
    finally:
        if proc.poll() is None:
            proc.kill()
    print("OK")


if __name__ == "__main__":
    main()
