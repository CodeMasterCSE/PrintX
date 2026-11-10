import asyncio
import json
from typing import Dict, Set, Any, Optional, AsyncGenerator
from app.core.logging import logger


def format_sse(event: str, data: Any) -> str:
    """Formats an event name and data payload into standard SSE format."""
    data_str = json.dumps(data) if not isinstance(data, str) else data
    return f"event: {event}\ndata: {data_str}\n\n"


class EventBroadcaster:
    """
    In-memory async Pub/Sub event broadcaster for Server-Sent Events (SSE).
    Supports concurrent client subscriptions per channel and safe broadcasting
    from both synchronous and asynchronous contexts.
    """

    def __init__(self):
        self._channels: Dict[str, Set[asyncio.Queue]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def get_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        if self._loop and self._loop.is_running():
            return self._loop
        try:
            loop = asyncio.get_running_loop()
            self._loop = loop
            return loop
        except RuntimeError:
            return None

    def subscribe(self, channel: str) -> asyncio.Queue:
        """Subscribes to a channel and returns an asyncio.Queue for receiving events."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        if channel not in self._channels:
            self._channels[channel] = set()
        self._channels[channel].add(queue)
        subscriber_count = len(self._channels[channel])
        logger.debug(f"SSE Subscribed to channel '{channel}' (Subscribers: {subscriber_count})")
        return queue

    def unsubscribe(self, channel: str, queue: asyncio.Queue):
        """Unsubscribes a queue from a channel."""
        if channel in self._channels:
            self._channels[channel].discard(queue)
            if not self._channels[channel]:
                del self._channels[channel]
        logger.debug(f"SSE Unsubscribed from channel '{channel}'")

    async def broadcast(self, channel: str, event: str, data: Any):
        """Asynchronously broadcasts an event payload to all active channel subscribers."""
        subscribers = list(self._channels.get(channel, []))
        if not subscribers:
            return

        payload = {"event": event, "data": data}
        for q in subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning(f"Subscriber queue full on channel '{channel}'. Dropping event.")

    def broadcast_sync(self, channel: str, event: str, data: Any):
        """
        Synchronously schedules an event broadcast.
        Safe to call from database hooks, synchronous routes, and worker threads.
        """
        loop = self.get_loop()
        if loop and loop.is_running():
            try:
                loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self.broadcast(channel, event, data))
                )
            except Exception as e:
                logger.debug(f"Failed to dispatch sync broadcast on channel '{channel}': {e}")
        else:
            logger.debug(f"No running event loop to broadcast on channel '{channel}'.")

    async def event_generator(
        self,
        channel: str,
        initial_data: Optional[Any] = None,
        initial_event: str = "message",
        keepalive_seconds: float = 15.0,
        request: Any = None,
        max_events: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Yields formatted SSE strings. Automatically sends an initial event if provided,
        streams incoming channel events, and emits periodic SSE keep-alive comments.
        Gracefully terminates if the client disconnects or if max_events is reached.
        """
        queue = self.subscribe(channel)
        emitted_count = 0
        try:
            if initial_data is not None:
                yield format_sse(initial_event, initial_data)
                emitted_count += 1
                if max_events is not None and emitted_count >= max_events:
                    return

            while True:
                if request and hasattr(request, "is_disconnected") and await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=keepalive_seconds)
                    yield format_sse(item["event"], item["data"])
                    emitted_count += 1
                    if max_events is not None and emitted_count >= max_events:
                        break
                except asyncio.TimeoutError:
                    if request and hasattr(request, "is_disconnected") and await request.is_disconnected():
                        break
                    # SSE keep-alive ping comment to prevent intermediate proxy timeout
                    yield ": keepalive\n\n"
        finally:
            self.unsubscribe(channel, queue)


event_broadcaster = EventBroadcaster()
