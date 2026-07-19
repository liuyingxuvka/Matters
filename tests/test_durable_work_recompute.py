from matters.infrastructure.jobs.runner import DurableWorkQueue
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.revisions.corrections import RecomputeRequest
from matters.revisions.recompute import OriginalOwnerRecompute


def test_bounded_queue_pause_resume_terminal_and_restart(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    store = SQLiteStore(home, repo)
    queue = DurableWorkQueue(store, capacity=2)
    observed = []
    queue.register_handler("C7", lambda payload: observed.append(payload["value"]))
    queue.enqueue(job_id="job:1", owner_id="C7", payload={"value": 1})
    assert queue.pause("job:1").status == "paused"
    assert queue.resume("job:1").status == "queued"
    assert queue.run_next().status == "passed"
    assert observed == [1]
    restarted = DurableWorkQueue(store)
    assert restarted.status("job:1").status == "passed"


def test_original_owner_recompute_joins_terminal_results(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    store = SQLiteStore(home, repo)
    queue = DurableWorkQueue(store)
    calls = []
    queue.register_handler("C6", lambda payload: calls.append(("C6", payload)))
    queue.register_handler("C12", lambda payload: calls.append(("C12", payload)))
    owner = OriginalOwnerRecompute(queue)
    batch = owner.submit(
        (
            RecomputeRequest("revision:1", "C6", ("matter:1",)),
            RecomputeRequest("revision:1", "C12", ("projection:1",)),
        )
    )
    terminal = owner.run_to_terminal(batch)
    assert terminal.status == "passed"
    assert {item[0] for item in calls} == {"C6", "C12"}
