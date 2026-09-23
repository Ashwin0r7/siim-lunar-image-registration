"""The archive client backs off when told to, and only then.

EXP-023's first census lost 67 of 95 candidates to HTTP 429 because no caller
waited long enough. ``polite_get`` retries congestion (429 / 5xx / connection
errors), honours ``Retry-After``, and raises a real answer such as 404 at once.
"""

import pytest
import requests

from siim.ingest import lro_nac


class _Resp:
    def __init__(self, status, headers=None, url="https://example.invalid/x"):
        self.status_code, self.headers, self.url = status, headers or {}, url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)


def _script(monkeypatch, responses):
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(lro_nac.requests, "get", fake_get)
    return calls


def test_429_is_retried_honouring_retry_after(monkeypatch):
    calls = _script(monkeypatch, [_Resp(429, {"Retry-After": "7"}), _Resp(503), _Resp(200)])
    slept = []
    r = lro_nac.polite_get("https://example.invalid/x", sleep=slept.append)
    assert r.status_code == 200 and len(calls) == 3
    assert slept == [7.0, 30.0]                        # Retry-After, then 15 * 2**1


def test_404_is_an_answer_not_congestion(monkeypatch):
    _script(monkeypatch, [_Resp(404)])
    slept = []
    with pytest.raises(requests.HTTPError):
        lro_nac.polite_get("https://example.invalid/x", sleep=slept.append)
    assert slept == []


def test_connection_errors_retry_then_give_up(monkeypatch):
    _script(monkeypatch, [requests.ConnectionError("reset")] * 3)
    slept = []
    with pytest.raises(requests.HTTPError, match="still refused after 3 attempts"):
        lro_nac.polite_get("https://example.invalid/x", tries=3, sleep=slept.append)
    assert slept == [15.0, 30.0, 60.0]


def test_waits_are_capped(monkeypatch):
    _script(monkeypatch, [_Resp(429, {"Retry-After": "99999"}), _Resp(200)])
    slept = []
    lro_nac.polite_get("https://example.invalid/x", sleep=slept.append, max_wait_s=300.0)
    assert slept == [300.0]
