import unittest
import rpy2.robjects as robjects
rinterface = robjects.rinterface
import array

class EnvironmentTestCase(unittest.TestCase):
    def testNew(self):
        env = robjects.Environment()
        self.assertEqual(rinterface.ENVSXP, env.typeof)

    def testNewValueError(self):
        self.assertRaises(ValueError, robjects.Environment, 'a')

    def testSetItem(self):
        env = robjects.Environment()
        env['a'] = 123
        self.assertTrue('a' in env)

def suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(EnvironmentTestCase)
    return suite

if __name__ == '__main__':
     unittest.main()
