"""Setup for ets python package."""
from os import path

from setuptools import find_packages, setup

THIS_DIRECTORY = path.abspath(path.dirname(__file__))
with open(path.join(THIS_DIRECTORY, "README.md"), encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

VERSION = {}
# pylint: disable=exec-used
with open(
    path.join(THIS_DIRECTORY, "xknxproject/__version__.py"), encoding="utf-8"
) as fp:
    exec(fp.read(), VERSION)

REQUIRES = ["cryptography>=35.0.0", "pyzipper>=0.3.5"]

setup(
    name="xknxproject",
    description="A library to gather information from ETS project files used for KNX",
    version=VERSION["__version__"],
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    download_url=f"https://github.com/XKNX/xknxproject/archive/{VERSION['__version__']}.zip",
    author="Marvin Wichmann",
    author_email="me@marvin-wichmann.de",
    license="GNU GPL",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    packages=find_packages(include=["xknxproject", "xknxproject.*"]),
    package_data={"xknxproject": ["py.typed"]},
    include_package_data=True,
    install_requires=REQUIRES,
    keywords="knx eib ets ets5 ets6",
    zip_safe=False,
)
