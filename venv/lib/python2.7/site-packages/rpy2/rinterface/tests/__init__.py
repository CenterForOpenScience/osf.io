import unittest

import test_SexpVector
import test_SexpEnvironment
import test_Sexp
import test_SexpClosure
import test_SexpVectorNumeric
import test_Device
import test_SexpExtPtr

import test_EmbeddedR
#import test_EmbeddedR_multithreaded


def suite():
    suite_SexpVector = test_SexpVector.suite()
    suite_SexpEnvironment = test_SexpEnvironment.suite()
    suite_Sexp = test_Sexp.suite()
    suite_SexpClosure = test_SexpClosure.suite()
    suite_SexpVectorNumeric = test_SexpVectorNumeric.suite()
    suite_EmbeddedR = test_EmbeddedR.suite()
    suite_Device = test_Device.suite()
    suite_SexpExtPtr = test_SexpExtPtr.suite()
    #suite_EmbeddedR_multithreaded = test_EmbeddedR_multithreaded.suite()
    alltests = unittest.TestSuite([
        suite_EmbeddedR
        ,suite_Sexp
        ,suite_SexpVector 
        ,suite_SexpEnvironment 
        ,suite_SexpClosure
        ,suite_SexpVectorNumeric
        #,suite_Device
        #,suite_EmbeddedR_multithreaded
        ,suite_SexpExtPtr
        ])
    return alltests


if __name__ == '__main__':    
    tr = unittest.TextTestRunner(verbosity = 2)
    suite = suite()
    tr.run(suite)
