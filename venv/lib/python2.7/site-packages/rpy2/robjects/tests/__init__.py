import unittest

import testRObject
import testVector
import testArray
import testDataFrame
import testFormula
import testFunction
import testEnvironment
import testRobjects
import testMethods
import testPackages
import testHelp
import testLanguage

# wrap this nicely so a warning is issued if no numpy present
import testNumpyConversions

# wrap this nicely so a warning is issued if no numpy present
import testPandasConversions

# mapped R libraries
import rpy2.robjects.lib.tests

def suite():
    suite_RObject = testRObject.suite()
    suite_Vector = testVector.suite()
    suite_Array = testArray.suite()
    suite_DataFrame = testDataFrame.suite()
    suite_Function = testFunction.suite()
    suite_Environment = testEnvironment.suite()
    suite_Formula = testFormula.suite()
    suite_Robjects = testRobjects.suite()
    suite_NumpyConversions = testNumpyConversions.suite()
    suite_PandasConversions = testPandasConversions.suite()
    suite_Methods = testMethods.suite()
    suite_Packages = testPackages.suite()
    suite_Help = testHelp.suite()
    suite_Language = testLanguage.suite()
    # lib
    suite_lib = rpy2.robjects.lib.tests.suite()
    alltests = unittest.TestSuite([suite_RObject,
                                   suite_Vector,                   
                                   suite_Array,
                                   suite_DataFrame,
                                   suite_Function,
                                   suite_Environment,
                                   suite_Formula,
                                   suite_Robjects,
                                   suite_Methods,
                                   suite_NumpyConversions,
                                   suite_PandasConversions,
                                   suite_Packages,
                                   suite_Help,
                                   suite_Language,
                                   suite_lib
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
