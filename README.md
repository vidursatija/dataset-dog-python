# Dataset Dog Python SDK
Python SDK for [Dataset Dog](https://github.com/vidursatija/dataset-dog-server]).

## Installation
```bash
python3 -m pip install git+https://github.com/vidursatija/dataset-dog-python.git
```

## Usage
```python3
from dataset_dog import DatasetDog


dd = DatasetDog("<API SERVER>", "<API KEY>")

@dd.record_function(frequency=0.5)
def api1(a: float = 1.0, b: float = 2.0) -> float:
    return a + b
```

- Skip recording sensitive arguments

```python3
# say `b` is a sensitive argument, and we don't want to record it
@dd.record_function(frequency=0.5, skip_args=["b"])
def api1(a: float = 1.0, b: float = 2.0) -> float:
    return a + b
```

## TODO
- Documentation
- Examples
- Pypi
