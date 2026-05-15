import asyncio
import pytest
from core.event_bus import EventBus, OrderbookEvent, SignalEvent

@pytest.mark.asyncio
async def test_subscribers_receive_published_events():
    bus = EventBus()
    queue = asyncio.Queue()
    bus.subscribe(OrderbookEvent, queue)
    event = OrderbookEvent(market_id='m1', token_id='tok1', bids=[(0.48, 100.0)], asks=[(0.52, 100.0)], timestamp=1000.0)
    await bus.publish(event)
    received = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert received.market_id == 'm1'

@pytest.mark.asyncio
async def test_non_subscribers_do_not_receive():
    bus = EventBus()
    queue = asyncio.Queue()
    bus.subscribe(SignalEvent, queue)
    event = OrderbookEvent('m1', 'tok1', [], [], 1000.0)
    await bus.publish(event)
    assert queue.empty()

@pytest.mark.asyncio
async def test_multiple_subscribers_all_receive():
    bus = EventBus()
    q1, q2 = asyncio.Queue(), asyncio.Queue()
    bus.subscribe(OrderbookEvent, q1)
    bus.subscribe(OrderbookEvent, q2)
    await bus.publish(OrderbookEvent('m1', 'tok1', [], [], 1000.0))
    assert not q1.empty()
    assert not q2.empty()
