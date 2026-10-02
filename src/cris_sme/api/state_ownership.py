"""Cooperative local-process ownership, not a distributed scan lease."""
from contextlib import contextmanager
import os
from pathlib import Path
import stat
from typing import Iterator


@contextmanager
def own_state(output_dir: Path, figure_dir: Path, database_path: Path) -> Iterator[None]:
    """Lock shared namespaces before recovery can mutate another API's runs.

    Persistent lock files must not be unlinked: doing so permits a second inode
    to be locked while the original owner is still using its descriptor.
    """
    try:
        import fcntl
    except ImportError as exc:
        raise RuntimeError("Local API state ownership requires POSIX file locking") from exc
    paths = {
        output_dir.resolve() / ".cris-api.lock",
        figure_dir.resolve() / ".cris-api.lock",
        database_path.resolve().with_name(database_path.resolve().name + ".cris-api.lock"),
    }
    descriptors: list[int] = []
    try:
        for path in sorted(paths):
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
            descriptors.append(descriptor)
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise RuntimeError("API state lock must be a regular file")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("Another local API owns the configured report, figure, or database state") from exc
        yield
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
