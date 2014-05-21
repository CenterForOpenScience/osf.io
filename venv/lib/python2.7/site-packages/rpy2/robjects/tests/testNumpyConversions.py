import unittest
import sys
import rpy2.robjects as robjects
r = robjects.r

try:
    import numpy
    has_numpy = True
    import rpy2.robjects.numpy2ri as rpyn
except:
    has_numpy = False


class MissingNumpyDummyTestCase(unittest.TestCase):
    def testMissingNumpy(self):
        self.assertTrue(False) # numpy is missing. No tests.

class NumpyConversionsTestCase(unittest.TestCase):

    def setUp(self):
        #self._py2ri = robjects.conversion.py2ri
        #self._ri2py = robjects.conversion.ri2py
        rpyn.activate()

    def tearDown(self):
        robjects.conversion.py2ri = robjects.default_py2ri
        robjects.conversion.ri2py = robjects.default_ri2py

    def checkHomogeneous(self, obj, mode, storage_mode):
        converted = robjects.conversion.py2ri(obj)
        self.assertEqual(r["mode"](converted)[0], mode)
        self.assertEqual(r["storage.mode"](converted)[0], storage_mode)
        self.assertEqual(list(obj), list(converted))
        self.assertTrue(r["is.array"](converted)[0])

    def testVectorBoolean(self):
        b = numpy.array([True, False, True], dtype=numpy.bool_)
        self.checkHomogeneous(b, "logical", "logical")

    def testVectorInteger(self):
        i = numpy.array([1, 2, 3], dtype="i")
        self.checkHomogeneous(i, "numeric", "integer")

    def testVectorFloat(self):
        f = numpy.array([1, 2, 3], dtype="f")
        self.checkHomogeneous(f, "numeric", "double")

    def testVectorComplex(self):
        c = numpy.array([1j, 2j, 3j], dtype=numpy.complex_)
        self.checkHomogeneous(c, "complex", "complex")

    def testVectorCharacter(self):
        if sys.version_info[0] == 3:
            # bail out - strings are unicode and this is tested next
            # test below
            return
        s = numpy.array(["a", "b", "c"], dtype="S")
        self.checkHomogeneous(s, "character", "character")

    def testVectorUnicodeCharacter(self):
        u = numpy.array([u"a", u"b", u"c"], dtype="U")
        self.checkHomogeneous(u, "character", "character")

    def testArray(self):

        i2d = numpy.array([[1, 2, 3], [4, 5, 6]], dtype="i")
        i2d_r = robjects.conversion.py2ri(i2d)

        self.assertEqual(r["storage.mode"](i2d_r)[0], "integer")
        self.assertEqual(tuple(r["dim"](i2d_r)), (2, 3))

        # Make sure we got the row/column swap right:
        self.assertEqual(i2d_r.rx(1, 2)[0], i2d[0, 1])

        f3d = numpy.arange(24, dtype="f").reshape((2, 3, 4))
        f3d_r = robjects.conversion.py2ri(f3d)

        self.assertEqual(r["storage.mode"](f3d_r)[0], "double")
        self.assertEqual(tuple(r["dim"](f3d_r)), (2, 3, 4))

        # Make sure we got the row/column swap right:
        self.assertEqual(f3d_r.rx(1, 2, 3)[0], f3d[0, 1, 2])

    def testObjectArray(self):
        o = numpy.array([1, "a", 3.2], dtype=numpy.object_)
        o_r = robjects.conversion.py2ri(o)
        self.assertEqual(r["mode"](o_r)[0], "list")
        self.assertEqual(r["[["](o_r, 1)[0], 1)
        self.assertEqual(r["[["](o_r, 2)[0], "a")
        self.assertEqual(r["[["](o_r, 3)[0], 3.2)

    def testRecordArray(self):
        rec = numpy.array([(1, 2.3), (2, -0.7), (3, 12.1)],
                          dtype=[("count", "i"), ("value", numpy.double)])
        rec_r = robjects.conversion.py2ri(rec)
        self.assertTrue(r["is.data.frame"](rec_r)[0])
        self.assertEqual(tuple(r["names"](rec_r)), ("count", "value"))
        count_r = r["$"](rec_r, "count")
        value_r = r["$"](rec_r, "value")
        self.assertEqual(r["storage.mode"](count_r)[0], "integer")
        self.assertEqual(r["storage.mode"](value_r)[0], "double")
        self.assertEqual(count_r[1], 2)
        self.assertEqual(value_r[2], 12.1)

    def testBadArray(self):
        u = numpy.array([1, 2, 3], dtype=numpy.uint32)
        self.assertRaises(ValueError, robjects.conversion.py2ri, u)

    def testAssignNumpyObject(self):
        x = numpy.arange(-10., 10., 1)
        env = robjects.Environment()
        env["x"] = x
        self.assertEqual(1, len(env))
        self.assertTrue(isinstance(env["x"], robjects.Array))

    def testDataFrameToNumpy(self):
        df = robjects.vectors.DataFrame(dict((('a', 1), ('b', 2))))
        reca = rpyn.ri2numpy(df)
        self.assertTrue(isinstance(reca, numpy.recarray))
        self.assertEqual(1, reca.a[0])
        self.assertEqual(2, reca.b[0])

    def testAtomicVectorToNumpy(self):
        v = robjects.vectors.IntVector((1,2,3))
        a = rpyn.ri2numpy(v)
        self.assertTrue(isinstance(a, numpy.ndarray))
        self.assertEqual(1, v[0])

    def testListVectorToNumpyErrorShape(self):
        vec = robjects.ListVector({'a': robjects.vectors.IntVector((1, 2, 3)), 
                                   'b': 2})
        self.assertRaises(ValueError, rpyn.ri2numpy, vec)

def suite():
    if has_numpy:
        return unittest.TestLoader().loadTestsFromTestCase(NumpyConversionsTestCase)
    else:
        return unittest.TestLoader().loadTestsFromTestCase(MissingNumpyDummyTestCase)

if __name__ == '__main__':
    unittest.main()

