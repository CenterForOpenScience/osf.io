if __name__ == "__main__":
    import sys, rpy2.rinterface
    sys.stdout.write("rpy2 version: %s\n" % rpy2.__version__)
    sys.stdout.write("built against R version: %s\n" % '-'.join(str(x) for x in rpy2.rinterface.R_VERSION_BUILD))
    sys.stdout.flush()

import unittest

import rpy2.robjects.tests
import rpy2.rinterface.tests
import rpy2.rlike.tests
#import rpy2.interactive.tests

import rpy2.tests_rpy_classic

def suite():
    suite_robjects = rpy2.robjects.tests.suite()
    suite_rinterface = rpy2.rinterface.tests.suite()
    suite_rlike = rpy2.rlike.tests.suite()
    #suite_interactive = rpy2.interactive.tests.suite()

    suite_rpy_classic = rpy2.tests_rpy_classic.suite()

    alltests = unittest.TestSuite([suite_rinterface,
                                   suite_robjects, 
                                   suite_rlike,
                                   #suite_interactive,
                                   suite_rpy_classic
                                   ])
    return alltests

if __name__ == "__main__":
    unittest.main(defaultTest = "suite")

