import cProfile
import os
import unittest
import pyprof

CODE = """
def a():
    b()

def b():
    c()

def c():
    pass

if __name__ == '__main__':
    a()
"""


class TestProfile(unittest.TestCase):
    def tearDown(self):
        os.unlink('test_profile_data')

    def test_profiling(self):
        cProfile.run(CODE, 'test_profile_data')
        profile = pyprof.Profile('test_profile_data')
        report = profile.build_report()
