import os
from struct import error
import pandas
from pandas.util.testing import assert_frame_equal
from nose.tools import *
from pandas.parser import CParserError
from rpy2.rinterface import RRuntimeError
from xlrd.biffh import XLRDError
from .utilities import row_population, column_population,\
    MAX_COLS, MAX_ROWS, check_shape, TooBigError
from .renderers import CSVRenderer, STATARenderer, ExcelRenderer, SPSSRenderer


here, _ = os.path.split(os.path.abspath(__file__))


class TestCSV(unittest.TestCase):
    def setUp(self):
        self.renderer = CSVRenderer()

    # Test renderer
    def test_build_df_csv(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.csv'))
        df = self.renderer._build_df(file_pointer)
        test_df = pandas.DataFrame(index=[0, 1, 2, 3])
        test_df['A'] = [1, 2, 3, 4]
        test_df['B'] = [2, 3, 4, 5]
        assert_frame_equal(df, test_df)

    def test_row_population_csv(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.csv'))
        df = self.renderer._build_df(file_pointer)
        rows = row_population(df)
        test_rows = [{'A': '1', 'B': '2'}, {'A': '2', 'B': '3'},
                    {'A': '3', 'B': '4'}, {'A': '4', 'B': '5'}]
        assert_true(rows == test_rows)

    def test_column_population_csv(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.csv'))
        df = self.renderer._build_df(file_pointer)
        cols = column_population(df)
        test_cols = [{'field': u'A', 'id': u'A', 'name': u'A'},
                     {'field': u'B', 'id': u'B', 'name': u'B'}]
        assert_true(cols == test_cols)

    def test_shape_csv(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.csv'))
        df = self.renderer._build_df(file_pointer)
        assert_true(df.shape == (4, 2))

    def test_blank_error_csv(self):
        file_pointer = open(os.path.join(here, 'fixtures/blank.csv'))
        self.assertRaises(CParserError, self.renderer._build_df, file_pointer)

        ##### General shape check #####

    def test_TooBigError_csv(self):
        num_rows = MAX_ROWS+1
        num_cols = MAX_COLS+1
        test_df = pandas.DataFrame(index=range(num_rows))
        for n in range(num_cols):
            test_df[n] = [0] * num_rows
        print test_df.shape
        self.assertRaises(TooBigError, check_shape, test_df)


class TestSTATA(unittest.TestCase):
    def setUp(self):
        self.renderer = STATARenderer()

    # Test renderer
    def test_build_df_dta(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.dta'))
        df = self.renderer._build_df(file_pointer)
        test_df = pandas.DataFrame(index=[0, 1, 2, 3])
        test_df['A'] = [1, 2, 3, 4]
        test_df['B'] = [2, 3, 4, 5]
        assert_frame_equal(df, test_df)

    def test_row_population_dta(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.dta'))
        df = self.renderer._build_df(file_pointer)
        rows = row_population(df)
        # STATA DTA files default to int
        test_rows = [{'A': '1', 'B': '2'}, {'A': '2', 'B': '3'},
                    {'A': '3', 'B': '4'}, {'A': '4', 'B': '5'}]
        print rows
        print test_rows
        print rows == test_rows
        assert_true(rows == test_rows)

    def test_column_population_dta(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.dta'))
        df = self.renderer._build_df(file_pointer)
        cols = column_population(df)
        test_cols = [{'field': u'A', 'id': u'A', 'name': u'A'},
                     {'field': u'B', 'id': u'B', 'name': u'B'}]
        assert_true(cols == test_cols)

    def test_shape_dta(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.dta'))
        df = self.renderer._build_df(file_pointer)
        assert_true(df.shape == (4, 2))

    def test_blank_error_dta(self):
        file_pointer = open(os.path.join(here, 'fixtures/blank.dta'))
        self.assertRaises(ValueError, self.renderer._build_df, file_pointer)

    def test_broken_dta(self):
        file_pointer = open(os.path.join(here, 'fixtures/broken.dta'))
        self.assertRaises(error, self.renderer._build_df, file_pointer)


class TestExcel(unittest.TestCase):
    def setUp(self):
        self.renderer = ExcelRenderer()

    #######
    # XLS #
    #######
    def test_build_df_xls(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.xls'))
        df = self.renderer._build_df(file_pointer)
        test_df = pandas.DataFrame(index=[0, 1, 2, 3])
        test_df['A'] = [1.0, 2.0, 3.0, 4.0]
        test_df['B'] = [2.0, 3.0, 4.0, 5.0]
        print df
        print test_df
        assert_frame_equal(df, test_df)

    def test_row_population_xls(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.xls'))
        df = self.renderer._build_df(file_pointer)
        rows = row_population(df)
        test_rows = [{u'A': '1.0', u'B': '2.0'}, {u'A': '2.0', u'B': '3.0'},
                   {u'A': '3.0', u'B': '4.0'}, {u'A': '4.0', u'B': '5.0'}]
        assert_true(rows == test_rows)

    def test_column_population_xls(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.xls'))
        df = self.renderer._build_df(file_pointer)
        cols = column_population(df)
        test_cols = [{'field': u'A', 'id': u'A', 'name': u'A'},
                     {'field': u'B', 'id': u'B', 'name': u'B'}]
        assert_true(cols == test_cols)

    def test_shape_xls(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.xls'))
        df = self.renderer._build_df(file_pointer)
        assert_true(df.shape == (4, 2))

    def test_blank_error_xls(self):
        file_pointer = open(os.path.join(here, 'fixtures/blank.xls'))
        self.assertRaises(IndexError, self.renderer._build_df, file_pointer)

    def test_broken_xls(self):
        file_pointer = open(os.path.join(here, 'fixtures/broken.xls'))
        self.assertRaises(XLRDError, self.renderer._build_df, file_pointer)

    ########
    # XLSX #
    ########
    def test_build_df_xlsx(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.xlsx'))
        df = self.renderer._build_df(file_pointer)
        test_df = pandas.DataFrame(index=[0, 1, 2, 3])
        test_df['A'] = [1.0, 2.0, 3.0, 4.0]
        test_df['B'] = [2.0, 3.0, 4.0, 5.0]
        assert_frame_equal(df, test_df)

    def test_row_population_xlsx(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.xlsx'))
        df = self.renderer._build_df(file_pointer)
        rows = row_population(df)
        # xlsx files default to float
        test_rows = [{u'A': '1.0', u'B': '2.0'}, {u'A': '2.0', u'B': '3.0'},
                   {u'A': '3.0', u'B': '4.0'}, {u'A': '4.0', u'B': '5.0'}]
        assert_true(rows == test_rows)

    def test_column_population_xlsx(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.xlsx'))
        df = self.renderer._build_df(file_pointer)
        cols = column_population(df)
        test_cols = [{'field': u'A', 'id': u'A', 'name': u'A'},
                     {'field': u'B', 'id': u'B', 'name': u'B'}]
        assert_true(cols == test_cols)

    def test_shape_xlsx(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.xlsx'))
        df = self.renderer._build_df(file_pointer)
        assert_true(df.shape == (4, 2))

    def test_blank_error_xlsx(self):
        file_pointer = open(os.path.join(here, 'fixtures/blank.xlsx'))
        self.assertRaises(IndexError, self.renderer._build_df, file_pointer)

    def test_broken_xlsx(self):
        file_pointer = open(os.path.join(here, 'fixtures/broken.xlsx'))
        self.assertRaises(XLRDError, self.renderer._build_df, file_pointer)


class TestSPSS(unittest.TestCase):
    def setUp(self):
        self.renderer = SPSSRenderer()

    # Test renderer
    def test_build_df_sav(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.sav'))
        df = self.renderer._build_df(file_pointer)
        test_df = pandas.DataFrame(index=[0, 1, 2, 3])
        # SPSS vals default to float
        test_df['A'] = [1.0, 2.0, 3.0, 4.0]
        test_df['B'] = [2.0, 3.0, 4.0, 5.0]
        print test_df

        assert_frame_equal(df, test_df)

    def test_row_population_sav(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.sav'))
        df = self.renderer._build_df(file_pointer)
        rows = row_population(df)
        # SPSS vals default to float
        test_rows = [{u'A': '1.0', u'B': '2.0'}, {u'A': '2.0', u'B': '3.0'},
                   {u'A': '3.0', u'B': '4.0'}, {u'A': '4.0', u'B': '5.0'}]
        print rows
        print test_rows
        print rows == test_rows
        assert_true(rows == test_rows)

    def test_column_population_sav(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.sav'))
        df = self.renderer._build_df(file_pointer)
        cols = column_population(df)
        test_cols = [{'field': u'A', 'id': u'A', 'name': u'A'},
                     {'field': u'B', 'id': u'B', 'name': u'B'}]
        assert_true(cols == test_cols)

    def test_shape_sav(self):
        file_pointer = open(os.path.join(here, 'fixtures/test.sav'))
        df = self.renderer._build_df(file_pointer)
        assert_true(df.shape == (4, 2))

    def test_broken_sav(self):
        file_pointer = open(os.path.join(here, 'fixtures/broken.sav'))
        self.assertRaises(RRuntimeError, self.renderer._build_df, file_pointer)
