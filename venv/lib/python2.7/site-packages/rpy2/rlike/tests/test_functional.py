import unittest
import itertools
import rpy2.rlike.functional as rlf

class TapplyTestCase(unittest.TestCase):

    def testSumByString(self):
        seq  = (  1,   2,   3,   4,   5,   6)
        tags = ('a', 'b', 'a', 'c', 'b', 'a')
        expected = {'a': 1+3+6,
                    'b': 2+5,
                    'c': 4}
        res = rlf.tapply(seq, tags, sum)
        for k, v in res:
            self.assertEqual(expected[k], v)

class VectorizeTestCase(unittest.TestCase):

    def simpleFunction(self, subject_fun):
        def f(x):
            return x ** 2
        f_iter = subject_fun(f)

        seq = (1, 2, 3)
        res = f_iter(seq)

        for va, vb in itertools.izip(seq, res):
            self.assertEqual(va ** 2, vb)

    def testIterify(self):
        self.simpleFunction(rlf.iterify)

    def testListify(self):
        self.simpleFunction(rlf.listify)



def suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(TapplyTestCase)
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(VectorizeTestCase))
    return suite

if __name__ == '__main__':
     unittest.main()
