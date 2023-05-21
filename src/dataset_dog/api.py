import base64
import functools
import inspect
import os
import pickle
import random
import signal
from typing import Any, Callable, Dict, Tuple

from . import datamodels, worker

class DatasetDog:
    def __init__(self, server_url: str, project_id: str, project_secret: str):
        api_key = base64.b64encode(f"{project_id}:{project_secret}".encode()).decode(
            "utf-8"
        )
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
        try:
            b64_args = pickle.dumps(args)
            b64_kwargs = pickle.dumps(kwargs)
            b64_res = pickle.dumps(res)
            function_info = datamodels.FunctionInformation(
                function_name=function_name,
                args=b64_args,
                kwargs=b64_kwargs,
                res=b64_res,
            )
        except Exception as e:
            print(e)
            return
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
            func_module = inspect.getmodule(func)
            if func_module is None:
                raise Exception(
                    f"DatasetDog: Failed to record function {function_name}."
                    " Functions must be defined in a module."
                )
            module_path = func_module.__file__
            if not module_path:
                raise Exception(
                    f"DatasetDog: Failed to record function {function_name}."
                    " Functions must be defined in a module."
                )
            function_path = os.path.abspath(module_path)[:-3]
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
