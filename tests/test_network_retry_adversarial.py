"""
Milestone 3 Adversarial Challenge: Network Retry & Self-Healing Stress Suite.
Author / Challenger: challenger_m3_2
Repository Target: /media/vpsg16gb/Media/historysnooze

Adversarial Objectives:
1. Inject transient HTTP 429, 500, 502, 503, 504 errors into @retry_network_op.
2. Inject transient timeouts (TimeoutError, socket.timeout, URLError) and network drops.
3. Verify exact retry counts:
   - Behavior under max_retries=3 (attempts vs retries)
   - Behavior under max_retries=4 (exact 3 retries)
   - Recovery on attempt 2, 3, or exhaustion and re-raise.
4. Verify exponential backoff delay progression (delay = initial_delay * backoff_factor^(attempt-1)).
5. Verify both implementations:
   - 00.codebases/retry_handler.py (sync & async)
   - 00.codebases/network_retry.py & hsnooze.render/network_retry.py (sync)
6. Verify production wrapped network operations:
   - call_gemini_api
   - fetch_pending_rows_from_sheets
   - update_row_status_in_sheets
   - fetch_keyframe_bundle_cdn
   - connect_playwright_cdp
   - execute_playwright_cdp_call
7. Test fail-fast non-retryable exceptions and edge cases.
8. Uncover design flaw: Default `exceptions=(Exception,)` causes non-transient programming errors
   (TypeError, KeyError) to be retried across delay loops instead of failing fast.
"""

import asyncio
import http.client
import io
import json
import logging
import os
import socket
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, List
from unittest.mock import MagicMock, call, patch

# Configure sys.path for test target
REPO_ROOT = Path(__file__).resolve().parent.parent
CODEBASES_DIR = REPO_ROOT / "00.codebases"
RENDER_DIR = REPO_ROOT / "hsnooze.render"
OMNI_DIR = REPO_ROOT / "hsnooze.omni"
MODULES_DIR = CODEBASES_DIR / "script_producer_modules"

for p in [str(CODEBASES_DIR), str(RENDER_DIR), str(OMNI_DIR), str(MODULES_DIR), str(REPO_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import retry_handler
import network_retry
from script_producer_modules.network_clients import (
    call_gemini_api,
    fetch_pending_rows_from_sheets,
    update_row_status_in_sheets,
)
from download_drive_assets import fetch_keyframe_bundle_cdn
from image_remote_sync import connect_playwright_cdp, execute_playwright_cdp_call


def _make_http_error(code: int, msg: str = "Error") -> urllib.error.HTTPError:
    """Constructs a realistic urllib.error.HTTPError instance."""
    return urllib.error.HTTPError(
        url="https://api.example.com/endpoint",
        code=code,
        msg=msg,
        hdrs=http.client.HTTPMessage(),
        fp=io.BytesIO(b"error body"),
    )


# ==============================================================================
# 1. Transient HTTP Error Injection (429, 500, 502, 503, 504)
# ==============================================================================
class TestTransientHttpErrorInjection(unittest.TestCase):
    """Stress-tests retry handlers against transient HTTP status codes."""

    def test_http_429_rate_limit_recovers_on_second_attempt(self):
        """Injected HTTP 429 on attempt 1 succeeds on attempt 2 (1 retry)."""
        calls = 0

        @retry_handler.retry_network_op(max_retries=3, initial_delay=0.001, backoff_factor=2.0)
        def rate_limited_api():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise _make_http_error(429, "Too Many Requests")
            return {"status": "ok", "calls": calls}

        result = rate_limited_api()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(calls, 2)

    def test_http_429_rate_limit_recovers_on_third_attempt(self):
        """Injected HTTP 429 on attempts 1 and 2 succeeds on attempt 3 (2 retries)."""
        calls = 0

        @network_retry.retry_network_op(max_retries=3, initial_delay=0.001, backoff_factor=2.0)
        def heavy_rate_limited():
            nonlocal calls
            calls += 1
            if calls < 3:
                raise _make_http_error(429, "Too Many Requests")
            return "recovered"

        result = heavy_rate_limited()
        self.assertEqual(result, "recovered")
        self.assertEqual(calls, 3)

    def test_http_429_exhaustion_reraises_exact_httperror(self):
        """Persistent HTTP 429 exhausts retries and re-raises HTTPError(429)."""
        calls = 0

        @retry_handler.retry_network_op(max_retries=3, initial_delay=0.001, backoff_factor=2.0)
        def persistent_429():
            nonlocal calls
            calls += 1
            raise _make_http_error(429, "Rate Limit Exceeded")

        with self.assertRaises(urllib.error.HTTPError) as ctx:
            persistent_429()
        self.assertEqual(ctx.exception.code, 429)
        self.assertEqual(calls, 3)

    def test_http_500_internal_server_error_eventual_success(self):
        """Transient HTTP 500 error recovers within max_retries."""
        calls = 0

        @network_retry.retry_network_op(max_retries=3, initial_delay=0.001)
        def flaky_server():
            nonlocal calls
            calls += 1
            if calls < 3:
                raise _make_http_error(500, "Internal Server Error")
            return "server_healthy"

        self.assertEqual(flaky_server(), "server_healthy")
        self.assertEqual(calls, 3)

    def test_http_503_service_unavailable_exhaustion(self):
        """Persistent HTTP 503 exhausts attempts and raises."""
        calls = 0

        @network_retry.retry_network_op(max_retries=3, initial_delay=0.001)
        def dead_server():
            nonlocal calls
            calls += 1
            raise _make_http_error(503, "Service Unavailable")

        with self.assertRaises(urllib.error.HTTPError) as ctx:
            dead_server()
        self.assertEqual(ctx.exception.code, 503)
        self.assertEqual(calls, 3)


# ==============================================================================
# 2. Transient Timeouts and Socket Drops Injection
# ==============================================================================
class TestTransientTimeoutsAndSocketDrops(unittest.TestCase):
    """Stress-tests network drops, timeouts, and socket disconnections."""

    def test_socket_timeout_recovers(self):
        """Transient socket.timeout succeeds after retries."""
        calls = 0

        @retry_handler.retry_network_op(max_retries=3, initial_delay=0.001)
        def socket_call():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise socket.timeout("timed out")
            return "socket_ok"

        self.assertEqual(socket_call(), "socket_ok")
        self.assertEqual(calls, 2)

    def test_urllib_urlerror_timed_out_recovers(self):
        """urllib.error.URLError wrapping timeout is retried."""
        calls = 0

        @network_retry.retry_network_op(max_retries=3, initial_delay=0.001)
        def url_call():
            nonlocal calls
            calls += 1
            if calls < 3:
                raise urllib.error.URLError("Connection timed out")
            return "url_ok"

        self.assertEqual(url_call(), "url_ok")
        self.assertEqual(calls, 3)

    def test_connection_reset_and_refused_recovers(self):
        """ConnectionResetError followed by ConnectionRefusedError recovers."""
        calls = 0

        @retry_handler.retry_network_op(max_retries=4, initial_delay=0.001)
        def glitchy_connection():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ConnectionResetError("Connection reset by peer")
            if calls == 2:
                raise ConnectionRefusedError("Connection refused")
            return "connected"

        self.assertEqual(glitchy_connection(), "connected")
        self.assertEqual(calls, 3)


# ==============================================================================
# 3. Exponential Backoff Delay & Timing Progression
# ==============================================================================
class TestExponentialBackoffTimingProgression(unittest.TestCase):
    """Verifies that retry delays follow strict exponential backoff."""

    @patch("time.sleep")
    def test_exponential_backoff_sequence_retry_handler(self, mock_sleep):
        """retry_handler backoff sequence matches delay = initial_delay * (factor ** (attempt - 1))."""
        calls = 0

        @retry_handler.retry_network_op(
            max_retries=3,
            initial_delay=1.5,
            backoff_factor=2.0,
        )
        def failing_task():
            nonlocal calls
            calls += 1
            raise ConnectionError(f"Attempt {calls} failed")

        with self.assertRaises(ConnectionError):
            failing_task()

        self.assertEqual(calls, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        delays = [arg[0][0] for arg in mock_sleep.call_args_list]
        self.assertAlmostEqual(delays[0], 1.5, places=5)
        self.assertAlmostEqual(delays[1], 3.0, places=5)

    @patch("time.sleep")
    def test_exponential_backoff_sequence_network_retry(self, mock_sleep):
        """network_retry backoff sequence matches current_delay *= backoff_factor."""
        calls = 0

        @network_retry.retry_network_op(
            max_retries=3,
            initial_delay=0.8,
            backoff_factor=3.0,
        )
        def failing_task():
            nonlocal calls
            calls += 1
            raise OSError(f"Attempt {calls} failed")

        with self.assertRaises(OSError):
            failing_task()

        self.assertEqual(calls, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        delays = [arg[0][0] for arg in mock_sleep.call_args_list]
        self.assertAlmostEqual(delays[0], 0.8, places=5)
        self.assertAlmostEqual(delays[1], 2.4, places=5)

    @patch("time.sleep")
    def test_four_attempts_produces_three_retries_with_three_exponential_sleeps(self, mock_sleep):
        """max_retries=4 executes 1 initial call + 3 retries (total 4) with 3 backoff sleeps."""
        calls = 0

        @retry_handler.retry_network_op(
            max_retries=4,
            initial_delay=1.0,
            backoff_factor=2.0,
        )
        def four_try_task():
            nonlocal calls
            calls += 1
            raise ConnectionError("Persistent network outage")

        with self.assertRaises(ConnectionError):
            four_try_task()

        self.assertEqual(calls, 4)
        self.assertEqual(mock_sleep.call_count, 3)
        delays = [arg[0][0] for arg in mock_sleep.call_args_list]
        self.assertAlmostEqual(delays[0], 1.0, places=5)
        self.assertAlmostEqual(delays[1], 2.0, places=5)
        self.assertAlmostEqual(delays[2], 4.0, places=5)

    def test_real_wall_clock_elapsed_time_bounds(self):
        """Empirically validates wall-clock time elapsed for tiny delay backoff."""
        calls = 0
        t0 = time.perf_counter()

        @network_retry.retry_network_op(max_retries=3, initial_delay=0.015, backoff_factor=2.0)
        def timed_task():
            nonlocal calls
            calls += 1
            raise ConnectionError("Glitch")

        with self.assertRaises(ConnectionError):
            timed_task()

        elapsed = time.perf_counter() - t0
        # Expected minimum sleep: 0.015 + 0.030 = 0.045s
        self.assertGreaterEqual(elapsed, 0.040)


# ==============================================================================
# 4. Exception Filtering and Fail-Fast Invariants
# ==============================================================================
class TestExceptionFilteringAndFailFast(unittest.TestCase):
    """Verifies that non-matching exceptions bypass retry loops immediately."""

    @patch("time.sleep")
    def test_unmatched_exception_fails_fast_with_zero_retries(self, mock_sleep):
        """ValueError bypasses retries when only urllib.error.HTTPError is configured."""
        calls = 0

        @retry_handler.retry_network_op(
            max_retries=3,
            initial_delay=1.0,
            exceptions=(urllib.error.HTTPError,)
        )
        def strict_api():
            nonlocal calls
            calls += 1
            raise ValueError("Invalid parameters - should fail fast")

        with self.assertRaises(ValueError):
            strict_api()

        self.assertEqual(calls, 1)
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    def test_single_exception_type_passed_as_class_not_tuple(self, mock_sleep):
        """Passing a single Exception class (not in a tuple) is normalized and retried."""
        calls = 0

        @retry_handler.retry_network_op(
            max_retries=3,
            initial_delay=1.0,
            exceptions=ConnectionError
        )
        def single_exc_func():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise ConnectionError("Drop")
            return "ok"

        res = single_exc_func()
        self.assertEqual(res, "ok")
        self.assertEqual(calls, 2)
        mock_sleep.assert_called_once_with(1.0)

    @patch("time.sleep")
    def test_adversarial_vulnerability_typeerror_retried_due_to_generic_exception(self, mock_sleep):
        """
        Adversarial Finding: Because the default is exceptions=(Exception,),
        a fatal programming bug (e.g. TypeError, NameError) is erroneously retried
        multiple times with exponential backoff delay instead of failing fast.
        """
        calls = 0

        @retry_handler.retry_network_op(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
        def buggy_code():
            nonlocal calls
            calls += 1
            # Programming bug, not a network failure
            return None["missing_key"]

        with self.assertRaises(TypeError):
            buggy_code()

        # Adversarial proof: It called the buggy code 3 times and slept twice!
        self.assertEqual(calls, 3)
        self.assertEqual(mock_sleep.call_count, 2)


# ==============================================================================
# 5. Asynchronous Coroutine Support (retry_handler.py)
# ==============================================================================
class TestAsyncCoroutineRetry(unittest.TestCase):
    """Stress-tests async coroutine retry functionality in retry_handler.py."""

    def test_async_function_recovers_with_asyncio_sleep(self):
        """Async function failing with HTTP 429 recovers on attempt 2."""
        calls = 0

        @retry_handler.retry_network_op(max_retries=3, initial_delay=0.005, backoff_factor=2.0)
        async def async_fetch():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise _make_http_error(429, "Rate limited async")
            return "async_success"

        res = asyncio.run(async_fetch())
        self.assertEqual(res, "async_success")
        self.assertEqual(calls, 2)

    def test_async_function_exhaustion_raises(self):
        """Async function failing persistently exhausts attempts and raises."""
        calls = 0

        @retry_handler.retry_network_op(max_retries=3, initial_delay=0.005)
        async def async_failing():
            nonlocal calls
            calls += 1
            raise TimeoutError("Async timeout")

        with self.assertRaises(TimeoutError):
            asyncio.run(async_failing())
        self.assertEqual(calls, 3)


# ==============================================================================
# 6. Production Wrapped Network Functions Stress-Testing
# ==============================================================================
class TestProductionWrappedNetworkOperations(unittest.TestCase):
    """Injects faults directly into production functions decorated with @retry_network_op."""

    @patch("urllib.request.urlopen")
    def test_call_gemini_api_recovers_from_transient_429(self, mock_urlopen):
        """call_gemini_api recovers from HTTP 429 and parses Gemini response."""
        resp_payload = {
            "candidates": [
                {"content": {"parts": [{"text": "Part 01: The Dimming begins..."}]}}
            ]
        }
        mock_success = MagicMock()
        mock_success.read.return_value = json.dumps(resp_payload).encode("utf-8")
        mock_success.__enter__.return_value = mock_success

        mock_urlopen.side_effect = [
            _make_http_error(429, "Resource Exhausted"),
            mock_success,
        ]

        with patch("time.sleep"):
            text = call_gemini_api(prompt="Test Prompt", api_key="dummy_test_key")

        self.assertEqual(text, "Part 01: The Dimming begins...")
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("urllib.request.urlopen")
    def test_call_gemini_api_exhausts_and_raises_on_persistent_500(self, mock_urlopen):
        """call_gemini_api exhausts retries and raises HTTPError 500."""
        mock_urlopen.side_effect = _make_http_error(500, "Internal Server Error")

        with patch("time.sleep"):
            with self.assertRaises(urllib.error.HTTPError):
                call_gemini_api(prompt="Test Prompt", api_key="dummy_test_key")

        self.assertEqual(mock_urlopen.call_count, 3)

    @patch("script_producer_modules.network_clients.os.path.exists", return_value=True)
    def test_fetch_pending_rows_from_sheets_retries_on_gspread_error(self, mock_pathexists):
        """fetch_pending_rows_from_sheets retries when gspread raises a transient error."""
        with patch.dict("sys.modules", {"gspread": MagicMock()}):
            import gspread
            mock_gc = MagicMock()
            gspread.service_account.return_value = mock_gc
            mock_sh = MagicMock()
            mock_gc.open_by_key.return_value = mock_sh
            mock_ws = MagicMock()
            mock_sh.worksheet.return_value = mock_ws

            # Attempt 1: raises ConnectionError, Attempt 2: returns records
            mock_ws.get_all_records.side_effect = [
                ConnectionResetError("Socket reset while fetching sheets records"),
                [{"Part": "1", "Status": "pending"}],
            ]

            with patch("time.sleep"):
                rows = fetch_pending_rows_from_sheets(
                    spreadsheet_id="test_sheet_id",
                    credentials_path="/fake/creds.json"
                )

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["Part"], "1")
            self.assertEqual(mock_ws.get_all_records.call_count, 2)

    @patch("script_producer_modules.network_clients.os.path.exists", return_value=True)
    def test_update_row_status_in_sheets_exhausts_on_connection_error(self, mock_pathexists):
        """update_row_status_in_sheets raises ConnectionError after retry exhaustion."""
        with patch.dict("sys.modules", {"gspread": MagicMock()}):
            import gspread
            mock_gc = MagicMock()
            gspread.service_account.return_value = mock_gc
            mock_sh = MagicMock()
            mock_gc.open_by_key.return_value = mock_sh
            mock_ws = MagicMock()
            mock_sh.worksheet.return_value = mock_ws
            mock_ws.find.side_effect = ConnectionResetError("Connection lost to Google Sheets")

            with patch("time.sleep"):
                with self.assertRaises(ConnectionResetError):
                    update_row_status_in_sheets(
                        row_id="1",
                        status="COMPLETED",
                        spreadsheet_id="test_sheet_id",
                        credentials_path="/fake/creds.json"
                    )

            self.assertEqual(mock_ws.find.call_count, 3)

    @patch("urllib.request.urlopen")
    @patch("download_drive_assets.safe_extract_tarball")
    def test_fetch_keyframe_bundle_cdn_recovers_from_http_503(self, mock_extract, mock_urlopen):
        """fetch_keyframe_bundle_cdn in download_drive_assets retries and succeeds."""
        # Use io.BytesIO so read() terminates cleanly when EOF is reached
        class MockHttpResponse(io.BytesIO):
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass

        mock_success = MockHttpResponse(b"fake tar content bytes")

        mock_urlopen.side_effect = [
            _make_http_error(503, "Service Unavailable"),
            mock_success,
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            bundle_tar = Path(tmp_dir) / "bundle.tar.gz"
            keyframes_dir = Path(tmp_dir) / "keyframes"

            with patch("time.sleep"):
                res = fetch_keyframe_bundle_cdn(bundle_tar, keyframes_dir)

            self.assertTrue(res)
            self.assertEqual(mock_urlopen.call_count, 2)
            mock_extract.assert_called_once_with(bundle_tar, keyframes_dir)

    def test_connect_playwright_cdp_retries_on_connection_refusal(self):
        """connect_playwright_cdp retries when remote Chrome CDP endpoint fails."""
        mock_playwright_module = MagicMock()
        mock_p = MagicMock()
        mock_playwright_module.sync_playwright.return_value.start.return_value = mock_p
        mock_browser = MagicMock()

        # Attempt 1: Connection error, Attempt 2: successful connect
        mock_p.chromium.connect_over_cdp.side_effect = [
            ConnectionError("Chrome DevTools listening port unreachable"),
            mock_browser,
        ]

        with patch.dict("sys.modules", {"playwright.sync_api": mock_playwright_module}):
            with patch("time.sleep"):
                p, browser = connect_playwright_cdp(cdp_url="http://localhost:9222")

        self.assertEqual(browser, mock_browser)
        self.assertEqual(mock_p.chromium.connect_over_cdp.call_count, 2)

    @patch("urllib.request.urlopen")
    def test_execute_playwright_cdp_call_recovers_from_timeout(self, mock_urlopen):
        """execute_playwright_cdp_call retries JSON-RPC command on socket timeout."""
        mock_success = MagicMock()
        mock_success.read.return_value = json.dumps({"id": 1, "result": {"result": {"value": "ok"}}}).encode("utf-8")
        mock_success.__enter__.return_value = mock_success

        mock_urlopen.side_effect = [
            socket.timeout("CDP read timeout"),
            mock_success,
        ]

        with patch("time.sleep"):
            res = execute_playwright_cdp_call(
                endpoint_url="http://127.0.0.1:49657",
                method="Runtime.evaluate",
                params={"expression": "1 + 1"},
            )

        self.assertEqual(res["result"]["result"]["value"], "ok")
        self.assertEqual(mock_urlopen.call_count, 2)


# ==============================================================================
# 7. Semantic Ambiguity Analysis: '3 Retries' vs '3 Attempts'
# ==============================================================================
class TestRetryCountSemanticAnalysis(unittest.TestCase):
    """
    Adversarial verification of whether max_retries represents:
    - Option A: Total attempts = max_retries (1 initial + (max_retries - 1) retries)
    - Option B: Total retries after initial = max_retries (1 initial + max_retries retries)
    """

    def test_option_a_max_retries_is_total_attempts(self):
        """Documents that current implementation treats max_retries=3 as 3 total attempts (2 retries)."""
        calls = 0

        @retry_handler.retry_network_op(max_retries=3, initial_delay=0.001)
        def count_calls():
            nonlocal calls
            calls += 1
            raise RuntimeError("Error")

        with self.assertRaises(RuntimeError):
            count_calls()

        # In current code: total attempts = 3, retries = 2
        self.assertEqual(calls, 3)

    def test_option_b_four_attempts_required_for_three_retries(self):
        """Documents that to guarantee 3 actual retries, max_retries=4 must be specified."""
        calls = 0

        @retry_handler.retry_network_op(max_retries=4, initial_delay=0.001)
        def count_calls():
            nonlocal calls
            calls += 1
            raise RuntimeError("Error")

        with self.assertRaises(RuntimeError):
            count_calls()

        # Initial attempt (1) + 3 retries (2, 3, 4) = 4 total calls
        self.assertEqual(calls, 4)


if __name__ == "__main__":
    unittest.main()
