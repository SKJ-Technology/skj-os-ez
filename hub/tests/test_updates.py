from threading import Event

from skj_hub.backends.base import UpdateItem, no_progress
from skj_hub.backends.fake import FakeBackend, demo_backends
from skj_hub.catalog.model import Source
from skj_hub.result import Problem
from skj_hub.updates.plan import UpdatePlan
from skj_hub.updates.rules import DriverState, RestartState, restart_state


def item(source, name, size=10, restart=False):
    return UpdateItem(source, name, name, "1", "2", size, restart)


# --- plan ---------------------------------------------------------------------------


def test_plan_orders_distro_flatpak_snap():
    plan = UpdatePlan.build(
        [item(Source.SNAP, "s"), item(Source.FLATPAK, "f"), item(Source.DISTRO, "d")]
    )
    assert [src for src, _ in plan.steps] == [Source.DISTRO, Source.FLATPAK, Source.SNAP]


def test_plan_totals_and_restart():
    plan = UpdatePlan.build(
        [item(Source.DISTRO, "kernel", 90, restart=True), item(Source.FLATPAK, "gimp", 10)]
    )
    assert plan.count == 2
    assert plan.download_size == 100
    assert plan.needs_restart


def test_empty_plan():
    plan = UpdatePlan.build([])
    assert plan.empty
    assert plan.count == 0
    assert not plan.needs_restart


def test_plan_skips_sources_without_updates():
    plan = UpdatePlan.build([item(Source.FLATPAK, "f")])
    assert [src for src, _ in plan.steps] == [Source.FLATPAK]


# --- restart rules ------------------------------------------------------------------

NEW = ["7.2.9-200.fc44.x86_64"]


def test_no_restart_needed():
    assert restart_state(False, [], None) is RestartState.NOT_NEEDED


def test_restart_ready_without_nvidia():
    assert restart_state(True, NEW, None) is RestartState.READY
    no_nvidia = DriverState(False, frozenset(), False)
    assert restart_state(True, NEW, no_nvidia) is RestartState.READY


def test_wait_while_akmods_builds():
    building = DriverState(True, frozenset(), True)
    assert restart_state(True, NEW, building) is RestartState.WAIT_FOR_DRIVER


def test_wait_until_module_exists_for_new_kernel():
    old_only = DriverState(True, frozenset({"7.2.8-200.fc44.x86_64"}), False)
    assert restart_state(True, NEW, old_only) is RestartState.WAIT_FOR_DRIVER


def test_ready_once_module_built():
    built = DriverState(True, frozenset(NEW), False)
    assert restart_state(True, NEW, built) is RestartState.READY


def test_restart_without_kernel_update_is_ready_even_with_nvidia():
    # e.g. a systemd update: no new kernel, nothing for akmods to build
    nvidia = DriverState(True, frozenset(), False)
    assert restart_state(True, [], nvidia) is RestartState.READY


# --- fake backend ---------------------------------------------------------------------


def test_fake_update_clears_items():
    b = FakeBackend(Source.FLATPAK, updates=[item(Source.FLATPAK, "f")])
    assert b.update(b.updates(), no_progress, Event()).ok
    assert b.updates() == []


def test_fake_failure_keeps_items():
    b = FakeBackend(
        Source.FLATPAK, updates=[item(Source.FLATPAK, "f")], fail_with=Problem.NO_NETWORK
    )
    r = b.update(b.updates(), no_progress, Event())
    assert r.problem is Problem.NO_NETWORK
    assert len(b.updates()) == 1


def test_fake_cancel():
    b = FakeBackend(Source.FLATPAK, updates=[item(Source.FLATPAK, "f")])
    cancel = Event()
    cancel.set()
    assert b.update(b.updates(), no_progress, cancel).problem is Problem.CANCELLED


def test_demo_catalog_has_every_source():
    assert {b.source for b in demo_backends()} == set(Source)
