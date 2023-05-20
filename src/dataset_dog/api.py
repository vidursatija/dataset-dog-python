import functools
import inspect
import os
import pickle
import random
import base64
from typing import Any, Callable, Dict, Tuple, List
import signal
from . import datamodels

from . import worker

class DatasetDog:
    def __init__(self, server_url: str, api_key: str):
        self.worker = worker.BackgroundWorker(server_url, api_key)
        self.worker.start()
        signal.signal(signal.SIGINT, self.worker.kill)
        signal.signal(signal.SIGTERM, self.worker.kill)

    def __del__(self):
        self.worker.kill()

    def _submit_callback(
        self,
        function_name: str,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        res: Any
    ):
        b64_args = base64.b64encode(pickle.dumps(args)).decode("utf-8")
        b64_kwargs = base64.b64encode(pickle.dumps(kwargs)).decode("utf-8")
        b64_res = base64.b64encode(pickle.dumps(res)).decode("utf-8")
        function_info = datamodels.FunctionInformation(
            function_name=function_name,
            args=b64_args,
            kwargs=b64_kwargs,
            res=b64_res,
        )
        self.worker.submit(function_info)

    @staticmethod
    def filter_arguments(args: Tuple[str], kwargs: Dict[str, Any], skip_args: List[str]) -> Tuple[List[str], Dict[str, Any]]:
        """Filter out arguments that should not be recorded

        :param args: arguments
        :param kwargs: keyword arguments
        :param skip_args: arguments to skip

        :return: filtered arguments
        """
        filtered_args = [arg for arg in args if arg not in skip_args]
        filtered_kwargs = {_key: _value for _key, _value in kwargs.items() if _key not in skip_args}

        return filtered_args, filtered_kwargs

    def record_function(self, frequency: float, skip_args: List[str] = []):
        assert frequency > 0 and frequency <= 1

        def decorator(func: Callable):
            function_name = func.__name__
            function_path = os.path.abspath(inspect.getmodule(func).__file__)[:-3]
            full_function_name = f"{function_path}.{function_name}"
            @functools.wraps(func)
            async def awrapper(*args, **kwargs):
                res = await func(*args, **kwargs)
                filtered_args, filtered_kwargs = self.filter_arguments(args, kwargs, skip_args)

                if random.random() < frequency:
                    self._submit_callback(full_function_name, filtered_args, filtered_kwargs, res)
                return res

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                res = func(*args, **kwargs)
                filtered_args, filtered_kwargs = self.filter_arguments(args, kwargs, skip_args)

                if random.random() < frequency:
                    self._submit_callback(full_function_name, filtered_args, filtered_kwargs, res)
                return res

            if inspect.iscoroutinefunction(func):
                return awrapper
            else:
                return wrapper

        return decorator

