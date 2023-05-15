from dataclasses import dataclass


@dataclass
class FunctionInformation:
    function_name: str
    args: str  # base64 encoded pickle
    kwargs: str  # base64 encoded pickle
    res: str  # base64 encoded pickle
