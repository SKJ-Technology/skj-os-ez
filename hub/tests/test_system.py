from skj_hub.system import kmod_kernels


def test_kmod_kernels_from_rpm_names():
    out = "kmod-nvidia-7.2.8-200.fc44.x86_64\nkmod-nvidia-7.2.9-200.fc44.x86_64\nkmod-nvidia\n"
    assert kmod_kernels(out) == {"7.2.8-200.fc44.x86_64", "7.2.9-200.fc44.x86_64"}


def test_kmod_kernels_ignores_other_packages():
    assert kmod_kernels("kmod-nvidia-common\nakmod-nvidia\n") == frozenset()


def test_akmods_active_exited_is_not_building():
    from skj_hub.system import akmods_building

    # oneshot + RemainAfterExit: "active" all day after the boot run
    assert not akmods_building("active\n", akmods_process=False)
    assert akmods_building("activating\n", akmods_process=False)
    assert akmods_building("inactive", akmods_process=True)
