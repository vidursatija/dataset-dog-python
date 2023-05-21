from dataclasses import dataclass


@dataclass
class FunctionInformation:
    function_name: str
    args: bytes  # encoded pickle
    kwargs: bytes  # encoded pickle
    res: bytes  # encoded pickle
