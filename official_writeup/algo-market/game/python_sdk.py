"""Simplified Python SDK for interacting with the trading simulation service.

The SDK mirrors the capabilities exposed in the web frontend:
- Connect to the WebSocket feed and keep the latest state in memory
- Provide helper methods for all REST endpoints (simulation control, market data, user orders)
- Allow users to subscribe to real-time events via callbacks or a thread-safe queue

Dependencies (install with pip):
    pip install requests websockets

Example
-------
>>> from sdk.python_sdk import SimulationClient
>>> client = SimulationClient()
>>> client.start()
>>> client.wait_until_connected(timeout=10)
>>> client.start_simulation()
>>> event = client.get_event(timeout=5)
>>> print(event)
>>> client.stop()
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from queue import SimpleQueue, Empty
from typing import Any, Callable, Dict, Iterable, List, Optional
import math

import requests

try:  # pragma: no cover - optional dependency guard for static analysis
    import websockets  # type: ignore
except ImportError:
    websockets = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class SimulationState:
    """Keeps the latest snapshot of important simulation data."""

    connected: bool = False
    price_history: List[float] = field(default_factory=list)
    latest_tick: Optional[int] = None
    last_price: Optional[float] = None
    order_book: Dict[str, Any] = field(default_factory=dict)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    status: Dict[str, Any] = field(default_factory=dict)
    user_orders: List[Dict[str, Any]] = field(default_factory=list)
    portfolio: Dict[str, Any] = field(default_factory=dict)


class SimulationAPIError(RuntimeError):
    """Raised when the HTTP API returns an error."""


class SimulationClient:
    """Python SDK that wraps the trading simulation REST & WebSocket APIs."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        ws_url: Optional[str] = None,
        request_timeout: float = 10.0,
        reconnect_delay: float = 3.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.ws_url = ws_url or self._derive_ws_url(self.base_url)
        self.request_timeout = request_timeout
        self.reconnect_delay = reconnect_delay

        self.session = requests.Session()
        self.state = SimulationState()

        self._stop_event = threading.Event()
        self._connected_event = threading.Event()
        self._event_queue: "SimpleQueue[Dict[str, Any]]" = SimpleQueue()
        self._callbacks: List[Callable[[Dict[str, Any], "SimulationClient"], None]] = []
        self._callbacks_lock = threading.Lock()

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ws_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the background WebSocket listener."""
        if self._thread and self._thread.is_alive():
            logger.debug("SimulationClient already started")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_event_loop, name="SimulationClientWS", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the WebSocket listener and close resources."""
        self._stop_event.set()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(lambda: None)
        if self._thread:
            self._thread.join(timeout=5)
        self._connected_event.clear()
        self.state.connected = False
        self.session.close()

    def wait_until_connected(self, timeout: Optional[float] = None) -> bool:
        """Block until the WebSocket connection is established."""
        return self._connected_event.wait(timeout=timeout)

    def register_callback(self, callback: Callable[[Dict[str, Any], "SimulationClient"], None]) -> None:
        """Register a callback that receives every WebSocket event."""
        with self._callbacks_lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[Dict[str, Any], "SimulationClient"], None]) -> None:
        with self._callbacks_lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def get_event(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Retrieve the next WebSocket event from the thread-safe queue."""
        try:
            return self._event_queue.get(timeout=timeout)
        except Empty:
            return None

    # ------------------------------------------------------------------
    # Simulation control REST APIs
    # ------------------------------------------------------------------
    def start_simulation(self) -> Dict[str, Any]:
        return self._post("/simulation/start")

    def kill_simulation(self) -> Dict[str, Any]:
        return self._post("/simulation/kill")

    def set_tick_duration(self, tick_duration: float) -> Dict[str, Any]:
        payload = {"tick_duration": float(tick_duration)}
        return self._post("/simulation/tick-duration", json=payload)

    def send_truth(self, rating: float) -> Dict[str, Any]:
        payload = {"rating": float(rating)}
        return self._post("/simulation/send-truth", json=payload)

    def get_status(self) -> Dict[str, Any]:
        return self._get("/simulation/status")

    # ------------------------------------------------------------------
    # User trading REST APIs
    # ------------------------------------------------------------------
    def submit_user_order(
        self,
        direction: str,
        quantity: int,
        price: float,
        immediate_cancel: bool = False,
        valid_ticks: int = 9001,
    ) -> Dict[str, Any]:
        payload = {
            "direction": direction,
            "quantity": int(quantity),
            "price": float(price),
            "immediate_cancel": bool(immediate_cancel),
            "valid_ticks": int(valid_ticks),
        }
        response = self._post("/user/orders", json=payload)
        # Keep local state in sync
        self.refresh_user_orders()
        return response

    def cancel_user_order(self, order_id: str) -> Dict[str, Any]:
        response = self._post(f"/user/orders/{order_id}/cancel")
        self.refresh_user_orders()
        return response

    def list_user_orders(self) -> Dict[str, Any]:
        return self._get("/user/orders")

    def refresh_user_orders(self) -> None:
        try:
            result = self.list_user_orders()
            self.state.user_orders = result.get("open_orders", [])
            self.state.portfolio = result.get("portfolio", {})
        except SimulationAPIError:
            logger.exception("Failed to refresh user orders")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _run_event_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ws_task = self._loop.create_task(self._ws_consumer())
        try:
            self._loop.run_until_complete(self._ws_task)
        except Exception:
            logger.exception("WebSocket consumer crashed")
        finally:
            pending = asyncio.all_tasks(loop=self._loop)
            for task in pending:
                task.cancel()
            try:
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            self._loop.close()
            self._loop = None

    async def _ws_consumer(self) -> None:
        if websockets is None:
            raise ImportError("The 'websockets' package is required. Install it with 'pip install websockets'.")
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=20) as ws:
                    logger.info("Connected to WebSocket %s", self.ws_url)
                    self._set_connected(True)
                    await self._handle_ws_stream(ws)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._set_connected(False)
                if self._stop_event.is_set():
                    break
                logger.warning("WebSocket error: %s. Reconnecting in %.1fs", exc, self.reconnect_delay)
                await asyncio.sleep(self.reconnect_delay)
        self._set_connected(False)

    async def _handle_ws_stream(self, ws: Any) -> None:
        while not self._stop_event.is_set():
            try:
                raw = await ws.recv()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("WebSocket receive failed: %s", exc)
                break

            if raw is None:
                continue
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Received non-JSON payload: %s", raw)
                continue

            self._update_state_from_event(message)
            self._event_queue.put(message)
            self._dispatch_callbacks(message)

    def _dispatch_callbacks(self, message: Dict[str, Any]) -> None:
        with self._callbacks_lock:
            callbacks_snapshot = list(self._callbacks)
        for callback in callbacks_snapshot:
            try:
                callback(message, self)
            except Exception:
                logger.exception("Callback raised an exception")

    def _set_connected(self, value: bool) -> None:
        self.state.connected = value
        if value:
            self._connected_event.set()
        else:
            self._connected_event.clear()

    def _update_state_from_event(self, message: Dict[str, Any]) -> None:
        msg_type = message.get("type")
        if msg_type == "historical_prices":
            self.state.price_history = message.get("price_history", [])
            self.state.latest_tick = message.get("current_tick")
        elif msg_type == "tick_update":
            self.state.latest_tick = message.get("tick")
            self.state.last_price = message.get("last_price")
            self.state.order_book = message.get("order_book", {})
            self.state.trades = message.get("trades", [])
            user_orders = message.get("user_orders")
            if isinstance(user_orders, list):
                self.state.user_orders = user_orders
        elif msg_type == "status_update":
            self.state.status = message
        elif msg_type == "historical_data":
            # Full historical dump (used when late-subscribing)
            self.state.price_history = message.get("price_history", [])
            self.state.latest_tick = message.get("order_book_history", [{}])[-1].get("tick") if message.get("order_book_history") else None

    def _derive_ws_url(self, base_url: str) -> str:
        if base_url.startswith("https://"):
            return "wss://" + base_url[len("https://") :] + "/ws"
        if base_url.startswith("http://"):
            return "ws://" + base_url[len("http://") :] + "/ws"
        # Assume raw host:port
        return f"ws://{base_url}/ws"

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------
    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.request_timeout)
        response = self.session.request(method, url, **kwargs)
        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {"error": response.text or response.reason}
            raise SimulationAPIError(payload.get("error") or response.reason)
        if response.content:
            try:
                return response.json()
            except ValueError:
                return {"raw": response.text}
        return {}

    def _get(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        return self._request("POST", path, **kwargs)


__all__ = ["SimulationClient", "SimulationAPIError", "SimulationState"]

def get_tick_event(client):
    global sigma
    event = client.get_event(timeout=5)
    while not event or event.get("type") != "tick_update":
        event = client.get_event(timeout=5)
    return event


if __name__ == "__main__":
    client = SimulationClient(base_url="http://127.0.0.1:8080")
    client.start()
    client.wait_until_connected(timeout=10)

    client.start_simulation()

    client.set_tick_duration(0.01)

    for i in range(5):
        event = get_tick_event(client)
        print(f"Tick {event['tick']}: Price {event['last_price']}")

    client.submit_user_order(direction="buy", quantity=100, price=111)
