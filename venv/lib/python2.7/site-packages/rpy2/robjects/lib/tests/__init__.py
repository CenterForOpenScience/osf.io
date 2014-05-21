import unittest
from rpy2.rinterface import RRuntimeError

try:
    import test_ggplot2
except RRuntimeError:
    test_ggplot2 = None

def suite():
    if test_ggplot2:
        suite_ggplot2 = test_ggplot2.suite()
        alltests = unittest.TestSuite([suite_ggplot2, ])
    else:
        alltests = unittest.TestSuite([])
    return alltests
    #pass

def main():
    r = unittest.TestResult()
    suite().run(r)
    return r

if __name__ == '__main__':    
    tr = unittest.TextTestRunner(verbosity = 2)
    suite = suite()
    tr.run(suite)
