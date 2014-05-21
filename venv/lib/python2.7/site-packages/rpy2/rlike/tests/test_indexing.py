import unittest
import itertools
import rpy2.rlike.indexing as rfi

class OrderTestCase(unittest.TestCase):

    def testOrder(self):
        seq  = (  2,   1,   5,   3,   4)
        expected = (1, 2, 3, 4, 5)
        res = rfi.order(seq)
        for va, vb in itertools.izip(expected, res):
            self.assertEqual(va, seq[vb])


def suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(OrderTestCase)
    #suite.addTest(unittest.TestLoader().loadTestsFromTestCase(VectorizeTestCase))
    return suite

if __name__ == '__main__':
     unittest.main()
