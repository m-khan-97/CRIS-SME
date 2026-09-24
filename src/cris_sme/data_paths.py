"""Locate immutable defaults in a wheel or the source checkout, never by cwd."""

from pathlib import Path


def policy_data_path(filename: str) -> Path:
    if Path(filename).name != filename:
        raise ValueError("Policy asset must be a filename, not a path.")
    package = Path(__file__).resolve().parent
    bundled = package / "_data" / filename
    if bundled.is_file():
        return bundled
    source = package.parent.parent / "data" / filename
    if package.parent.name == "src" and source.is_file():
        return source
    raise FileNotFoundError(f"Required CRIS policy asset is missing: {filename}")
