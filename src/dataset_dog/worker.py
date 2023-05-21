"""
MIT License

Copyright (c) 2018 Functional Software, Inc. dba Sentry

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import asyncio
import base64
import gzip
import logging
import os
import queue
import threading
from typing import Any, Callable, Coroutine, Optional

import aiohttp

from . import datamodels

logger = logging.getLogger()

# callback type that is awaitable
CALLBACK_T = Callable[[], Coroutine[Any, Any, None]]


class BackgroundWorker:
    def __init__(self, server_url: str, api_key: str, max_tasks=2):
        self.server_url = server_url
        self.api_key = api_key
        self._tcp_conn = None
        self._loop = None
        self._queue: queue.Queue[
            Optional[datamodels.FunctionInformation]
        ] = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._thread_for_pid: Optional[int] = None
        self.max_tasks = max_tasks

    @property
    def is_alive(self) -> bool:
        if self._thread_for_pid != os.getpid():
            return False
        if not self._thread:
            return False
        return self._thread.is_alive()

    def _ensure_thread(self):
        if not self.is_alive:
            self.start()

    def start(self):
        if not self.is_alive:
            self._thread = threading.Thread(
                target=self._target, name="dataset_dog.BackgroundWorker"
            )
            self._thread.daemon = True
            self._thread.start()
            self._thread_for_pid = os.getpid()

    def kill(self, *args, **kwargs):
        """
        Kill worker thread. Returns immediately. Not useful for
        waiting on shutdown for events, use `flush` for that.
        """
        logger.debug("background worker got kill request")
        if self._thread:
            self._queue.put(None)

            self._thread.join()

            self._thread = None
            self._thread_for_pid = None

        logger.debug("background worker killed")

    def submit(self, function_info: datamodels.FunctionInformation) -> bool:
        self._ensure_thread()
        try:
            self._queue.put(function_info)
            return True
        except Exception:
            logger.error("Failed submitting job", exc_info=True)
            return False

    def _get_callback_function(
        self,
        function_info: datamodels.FunctionInformation,
    ) -> Callable[[], Coroutine[Any, Any, None]]:
        async def callback_fn():
            async with aiohttp.ClientSession(
                connector=self._tcp_conn,
                connector_owner=False,
                raise_for_status=True,
                loop=self._loop,
            ) as session:
                args = base64.b64encode(gzip.compress(function_info.args))
                kwargs = base64.b64encode(gzip.compress(function_info.kwargs))
                res = base64.b64encode(gzip.compress(function_info.res))
                async with session.post(
                    f"{self.server_url}/api/v1/function_records/",
                    json={
                        "functionName": function_info.function_name,
                        "dataType": "pickle",
                        "dataDump": {
                            "args": args,
                            "kwargs": kwargs,
                            "res": res,
                        },
                        "tags": {},  # TODO: add device info
                    },
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                ) as resp:
                    await resp.read()

        return callback_fn

    async def async_target(self):
        active_tasks = []
        while True:
            if len(active_tasks) >= self.max_tasks:
                try:
                    await asyncio.gather(*active_tasks)
                except Exception:
                    logger.error("Failed submitting job", exc_info=True)
                active_tasks = []
            function_info = self._queue.get()
            if function_info is None:
                logger.debug("background worker got None")
                break
            callback = self._get_callback_function(function_info)
            active_tasks.append(asyncio.create_task(callback()))
            self._queue.task_done()
            await asyncio.sleep(0)

        await asyncio.gather(*active_tasks)

    def _target(self):
        # create new loop because this is a new thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop

        # tcp conn needs to be in the same thread as the loop
        self._tcp_conn = aiohttp.TCPConnector(limit=self.max_tasks)
        logger.debug("Starting background worker")
        loop.run_until_complete(self.async_target())
