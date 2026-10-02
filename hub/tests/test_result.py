import pytest

from skj_hub.result import Problem, Result, classify


def test_success_is_ok():
    assert Result.success().ok


@pytest.mark.parametrize(
    "text, problem",
    [
        (
            "GDBus.Error:org.freedesktop.PolicyKit1.Error.NotAuthorized: not authorized",
            Problem.CANCELLED,
        ),
        ("Error writing to file: No space left on device", Problem.NO_SPACE),
        ("Curl error (6): Could not resolve host: mirrors.fedoraproject.org", Problem.NO_NETWORK),
        ("nothing provides libfoo.so.2 needed by bar-1.0", Problem.CONFLICT),
        ('snap "nosuchapp" not found', Problem.NOT_FOUND),
        (
            'cannot communicate with server: Post "http://localhost/v2/snaps": '
            "dial unix /run/snapd.socket: connect: no such file or directory",
            Problem.SERVICE_DOWN,
        ),
        ("something odd happened", Problem.UNKNOWN),
    ],
)
def test_classify(text, problem):
    r = classify(text)
    assert r.problem is problem
    assert r.details == text
    assert not r.ok


def test_classify_exception():
    assert classify(RuntimeError("Operation was cancelled")).problem is Problem.CANCELLED
