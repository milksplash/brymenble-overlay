"""Tests for ``overlay/server.py`` — the stdlib HTTP overlay server."""
import http.client
import json
import urllib.error
import urllib.request

from overlay.server import StateHolder, lan_ip, run_server


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def test_state_holder():
    holder = StateHolder()
    assert holder.get() == {"connected": False, "mode": "idle"}
    holder.set({"connected": True, "mode": "numeric"})
    assert holder.get() == {"connected": True, "mode": "numeric"}


def test_state_holder_mutate_atomic():
    holder = StateHolder()
    holder.set({"connected": True, "mode": "numeric", "value_digits": [1, 2, 3]})
    # mutate applies fn under one lock and returns the new state.
    new_state = holder.mutate(lambda s: {**s, "mode": "idle", "value_digits": []})
    assert new_state["mode"] == "idle"
    assert new_state["value_digits"] == []
    # The mutation is visible to subsequent get().
    assert holder.get()["mode"] == "idle"
    assert holder.get()["value_digits"] == []


def test_serves_state_json_and_assets():
    httpd, holder = run_server("127.0.0.1", 0)
    port = httpd.server_address[1]
    try:
        holder.set({"connected": True, "mode": "demo", "function": "DCV"})
        status, body, _ = _get(f"http://127.0.0.1:{port}/state.json")
        assert status == 200
        assert json.loads(body) == {
            "connected": True, "mode": "demo", "function": "DCV",
        }

        status, body, _ = _get(f"http://127.0.0.1:{port}/")
        assert status == 200
        assert b'<svg id="meter"' in body

        status, body, _ = _get(f"http://127.0.0.1:{port}/overlay.js")
        assert status == 200
        assert b"__bm_skins" in body
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_404_for_missing_file():
    httpd, _ = run_server("127.0.0.1", 0)
    port = httpd.server_address[1]
    try:
        status, _, _ = _get(f"http://127.0.0.1:{port}/nope.txt")
        assert status == 404
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_path_traversal_blocked():
    # A request outside web/ must be rejected (403), not served.
    httpd, _ = run_server("127.0.0.1", 0)
    port = httpd.server_address[1]
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request("GET", "/../README.md")
        resp = conn.getresponse()
        assert resp.status == 403
        resp.read()
        conn.close()
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_lan_ip_is_nonempty_string():
    addr = lan_ip()
    assert isinstance(addr, str)
    assert addr
