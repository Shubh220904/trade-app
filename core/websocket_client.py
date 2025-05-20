import asyncio
import websockets
import json
import threading
from queue import Queue
from .order_book import OrderBook
from config import OKX_WS_URL, SYMBOL


class OKXWebSocketClient:
    def __init__(self):
        self.order_book = OrderBook()
        self.data_queue = Queue()
        self.running = False
        self.thread = None

    async def _connect(self):
        async with websockets.connect(OKX_WS_URL) as ws:
            subscription = {
                "op": "subscribe",
                "args": [{"channel": "books5", "instId": SYMBOL}]
            }
            await ws.send(json.dumps(subscription))
            
            while self.running:
                try:
                    data = await ws.recv()
                    self._process_message(json.loads(data))
                except Exception as e:
                    print(f"WebSocket error: {e}")

    def _process_message(self, data):
        if 'data' in data:
            self.order_book.update(data)
            self.data_queue.put(data)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_async)
        self.thread.start()

    def _run_async(self):
        asyncio.run(self._connect())

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()