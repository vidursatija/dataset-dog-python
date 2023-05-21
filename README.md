# Dataset Dog Python SDK
Python SDK for [Dataset Dog](https://github.com/vidursatija/dataset-dog-server).

## Installation
```bash
python3 -m pip install git+https://github.com/vidursatija/dataset-dog-python.git
```

## Usage
```python
from dataset_dog import DatasetDog


dd = DatasetDog("<API SERVER>", "<PROJECT ID>", "<API SECRET>")

@dd.record_function(frequency=0.5)
def api1(a: float = 1.0, b: float = 2.0) -> float:
    return a + b
```
