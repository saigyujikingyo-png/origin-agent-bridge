import pytest

from origin_agent.datasets import inspect_dataset
from origin_agent.storage import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "state", [tmp_path])


@pytest.fixture
def dataset(store, tmp_path):
    path = tmp_path / "calibration.csv"
    path.write_text(
        "Concentration,Absorbance,Replicate,SD\n0,0.104,0.2,0.01\n1,0.290,0.4,0.02\n"
        "2,0.500,0.6,0.01\n3,0.710,0.8,0.02\n4,0.896,1.0,0.01\n",
        encoding="utf-8",
    )
    return inspect_dataset(store, str(path))


@pytest.fixture
def anyio_backend():
    return "asyncio"
