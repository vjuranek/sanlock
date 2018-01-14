"""
Test sanlock client operations.
"""

import io
import signal
import struct
import subprocess

import pytest

from . import util


def test_single_instance(sanlock_daemon):
    # Starting another instance while the daemon must fail.
    p = util.start_daemon()
    try:
        util.wait_for_termination(p, 1.0)
    except util.TimeoutExpired:
        p.kill()
        p.wait()
    assert p.returncode == 1


def test_start_after_kill():
    # After killing the daemon, next instance should be able to start.
    for i in range(5):
        p = util.start_daemon()
        try:
            util.wait_for_daemon(0.5)
        finally:
            p.kill()
            p.wait()
        assert p.returncode == -signal.SIGKILL


def test_client_failure():
    # No daemon is running, client must fail
    with pytest.raises(subprocess.CalledProcessError) as e:
        util.sanlock("client", "status")
    assert e.value.returncode == 1


def test_init_lockspace(tmpdir, sanlock_daemon):
    path = tmpdir.join("lockspace")
    with io.open(str(path), "wb") as f:
        # Poison with junk data.
        f.write(b"x" * 1024**2 + b"X" * 512)

    lockspace = "name:1:%s:0" % path
    util.sanlock("client", "init", "-s", lockspace)

    with io.open(str(path), "rb") as f:
        magic, = struct.unpack("< I", f.read(4))
        assert magic == 0x12212010

        # TODO: check more stuff here...

        # Do not modify data after the lockspace area.
        f.seek(1024**2, io.SEEK_SET)
        assert f.read(512) == b"X" * 512