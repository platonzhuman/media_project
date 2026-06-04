from concurrent.futures import ThreadPoolExecutor
from src.state import StateManager


def test_state_under_load(tmp_path):
    state = StateManager(state_path=tmp_path / "state.json")

    def worker(n):
        for _ in range(25):
            state.update(job_result={"output": f"/tmp/{n}.webp", "format": "webp",
                                     "saved_bytes": 100, "ratio": 10.0})

    with ThreadPoolExecutor(max_workers=4) as ex:
        for i in range(4):
            ex.submit(worker, i)

    data = state.get()
    assert data["total_processed"] == 100
    assert data["total_saved_bytes"] == 10000
