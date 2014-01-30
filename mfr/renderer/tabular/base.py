import os
from .. import FileRenderer
from .utilities import column_population, row_population, check_shape, MAX_COLS, MAX_ROWS, TooBigError
import json
from pandas.parser import CParserError
from struct import error
from rpy2.rinterface import RRuntimeError
from xlrd.biffh import XLRDError


class TabularRenderer(FileRenderer):
    def _render(self, file_pointer, **kwargs):
        _, file_name = os.path.split(file_pointer.name)
        _, ext = os.path.splitext(file_name)

        try:
            dataframe = self._build_df(file_pointer)
        except TooBigError:
            return """
                <div>There was an error rendering {file_name}</div><br>
                <div>Too many rows or columns</div>
                <div>Max rows x cols: {max_rows} x {max_cols} </div>
                """.format(
                file_name=file_name,
                max_rows=MAX_ROWS,
                max_cols=MAX_COLS,
            )

        except (IndexError, CParserError):
            return """
            <div>There was an error rendering {file_name}:</div><br>
            <div>Is this file blank?</div>
                """.format(file_name=file_name)

        except ValueError:
            if ext == ".dta":
                return """
                <div>There was an error rendering {file_name}:</div><br>
                <div> Version of given Stata file is not 104, 105, 108, 113 (Stata 8/9), 114 (Stata 10/11) or 115 (Stata 12) </div>
                <div> Is this a valid Stata file?</div>
                    """.format(file_name=file_name)
            else:
                raise Exception

        except (RRuntimeError, error, XLRDError):
            return """
                <div>There was an error rendering {file_name}:</div><br>
                <div> Is this a valid {ext} file?</div>
                    """.format(file_name=file_name, ext=ext)

        if dataframe is None:
            return """
        <div>There was an error rendering {file_name}</div><br>
        <div>Is it a valid {ext} file?</div>
        <div>Is it empty?</div>
        """.format(file_name=file_name, ext=ext)

        try:
            check_shape(dataframe)
        except TooBigError:
            return """
                <div>There was an error rendering {file_name}:</div><br>
                <div>Too many rows or columns: </div>
                <div>Max rows x cols = {max_rows} x {max_cols};
                 File rows x cols = {file_rows} x {file_cols}</div>
                """.format(
                file_name=file_name,
                max_rows=MAX_ROWS,
                max_cols=MAX_COLS,
                file_rows=dataframe.shape[0],
                file_cols=dataframe.shape[1],
            )

        columns = column_population(dataframe)
        rows = row_population(dataframe)
        return self._render_mako(
            "tabular.mako",
            columns=json.dumps(columns),
            rows=json.dumps(rows),
            STATIC_PATH=self.STATIC_PATH,
        )