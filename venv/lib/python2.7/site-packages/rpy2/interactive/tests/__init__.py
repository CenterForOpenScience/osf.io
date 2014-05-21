import unittest

import testRevents

def suite():
    suite_Revents = testRevents.suite()
    alltests = unittest.TestSuite([suite_Revents,
                                   ])
    return alltests

def main():
    r = unittest.TestResult()
    suite().run(r)
    return r

if __name__ == '__main__':    
    tr = unittest.TextTestRunner(verbosity = 2)
    suite = suite()
    tr.run(suite)
