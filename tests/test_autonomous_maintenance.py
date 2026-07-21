from types import SimpleNamespace

from matters.application.maintenance import AutonomousMaintenanceWorker


class _Ledger:
    def __init__(self, pending=()):
        self.pending = pending
        self.states = []

    def record_worker_state(self, *, worker_health, worker_checkpoint):
        self.states.append((worker_health, worker_checkpoint))

    def next_work(self, *, limit):
        return tuple(self.pending[:limit])


class _Operations:
    def pending_packages(self, *, offset, limit):
        raise AssertionError(
            "a worker without a Codex runner must not enumerate packages"
        )

    def redispatchable_packages(self, *, limit):
        return ()


class _Store:
    def __init__(self):
        self.rows = []

    def append(self, owner, object_id, revision, payload):
        self.rows.append((owner, object_id, revision, payload))


class _Dispatcher:
    def dispatch(self, package, result):
        raise AssertionError("no package can dispatch without a runner")


def test_worker_without_codex_runner_uses_indexed_backoff_state():
    ledger = _Ledger((("filesystem:user-document", "analysis"),))
    store = _Store()
    worker = AutonomousMaintenanceWorker(
        store=store,
        ledger=ledger,
        operations=_Operations(),
        dispatcher=_Dispatcher(),
        runner_provider=lambda: None,
        hierarchy_recovery=lambda _limit: (0, 0),
    )

    cycle = worker.run_cycle(limit=20)

    assert worker.interval_seconds == 30.0
    assert worker.background_cycle_limit == 1
    assert cycle.status == "waiting_for_codex"
    assert cycle.package_count == 0
    assert cycle.pending_work_count == 1
    assert cycle.checkpoint.endswith("pending=1:waiting_ai=1")
    assert ledger.states[-1][0] == "waiting_for_codex"
    assert store.rows[-1][0] == "maintenance_cycle"


def test_worker_without_pending_work_remains_idle():
    ledger = _Ledger()
    worker = AutonomousMaintenanceWorker(
        store=_Store(),
        ledger=ledger,
        operations=_Operations(),
        dispatcher=_Dispatcher(),
        runner_provider=lambda: None,
        hierarchy_recovery=lambda _limit: (0, 0),
    )

    cycle = worker.run_cycle(limit=20)

    assert cycle.status == "idle"
    assert cycle.pending_work_count == 0


def test_owner_redispatch_defers_new_analysis_expansion():
    package = SimpleNamespace(
        package_id="work:owner-recovery",
        input_fingerprint="sha256:owner-recovery",
    )
    result = SimpleNamespace(
        status="passed",
        receipt_current=True,
        package_input_fingerprint=package.input_fingerprint,
        auto_apply_status="blocked",
    )

    class RecoverableOperations:
        def redispatchable_packages(self, *, limit):
            assert limit == 20
            return ({"package_id": package.package_id},)

        def pending_packages(self, *, offset, limit):
            raise AssertionError(
                "owner recovery cannot enumerate new AI packages"
            )

        def package(self, package_id):
            assert package_id == package.package_id
            return package

        def current_result(self, package_id):
            assert package_id == package.package_id
            return result

    class RecoveringDispatcher:
        def dispatch(self, observed_package, observed_result):
            assert observed_package is package
            assert observed_result is result
            return (SimpleNamespace(status="auto_applied"),)

    worker = AutonomousMaintenanceWorker(
        store=_Store(),
        ledger=_Ledger(),
        operations=RecoverableOperations(),
        dispatcher=RecoveringDispatcher(),
        runner_provider=lambda: None,
        hierarchy_recovery=lambda _limit: (0, 0),
        analysis_expansion=lambda _limit: (_ for _ in ()).throw(
            AssertionError(
                "owner recovery must finish before new analysis expansion"
            )
        ),
    )

    cycle = worker.run_cycle(limit=20)

    assert cycle.status == "progressed"
    assert cycle.package_count == 1
    assert cycle.owner_redispatch_count == 1
    assert cycle.dispatched_count == 1
    assert cycle.analysis_expanded_source_count == 0
    assert cycle.analysis_queued_package_count == 0
    assert ":owner_retry=1:" in cycle.checkpoint
