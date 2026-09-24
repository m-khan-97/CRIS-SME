"""Package the canonical policy directory without maintaining a second copy."""

from setuptools import find_packages, setup


setup(
    packages=[*find_packages("src"), "cris_sme._data"],
    package_dir={"": "src", "cris_sme._data": "data"},
    package_data={"cris_sme._data": ["*.json"]},
    exclude_package_data={"cris_sme._data": ["finding_exceptions.json", "mute_rules.json"]},
)
