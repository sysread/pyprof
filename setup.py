import sys
from setuptools import setup, find_packages

if sys.version_info < (2, 5, 0):
    sys.stderr.write("Python 2.5 or newer is required.\n")
    sys.exit(-1)

setup(
    name = "pyprofile",
    version = "0.1",
    author = "Jeff Ober",
    author_email = "jeffober@gmail.com",
    description = "A report generator for python profiler data",
    keywords = "profile, profiler, profiling, report, html, analyze, analysis",
    url = "",
    license = "MIT",
    packages = find_packages(exclude=["*.tests", "*.tests.*"]),
    install_requires = ['pygments'],
    test_suite = 'pyprof.tests',
)
