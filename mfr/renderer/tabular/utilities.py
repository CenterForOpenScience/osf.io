class TooBigError(Exception):
    pass


def column_population(dataframe):
    """make column headers from the keys in dataframe
    :param dataframe:
    :return: a list of dictionaries
    """
    fields = dataframe.keys()

    print fields
    columns = [{'id': str(k), 'name': str(k), 'field': str(k), } for k in fields]
    return columns


def row_population(dataframe):
    """Convert the dictionary of lists Pandas has generated from the CSV into
    a list of dicts.
    :param dataframe:
    :return: JSON representation of rows
    """
    #todo this needs to be reformatted NOT to use the row names as a variable
    # to iterate over, this will break spss files that need rownames
    #todo right now it is renaming the rows in [r] when it reads it in
    fields = dataframe.keys()
    rows = []
    for n in range(len(dataframe[fields[0]])):
        rows.append({})
        for col_field in fields:
            rows[n][str(col_field)] = str(dataframe[col_field][n])
    return rows

MAX_COLS = 400
MAX_ROWS = 1000


def check_shape(dataframe):
    """ Takes a data_frame and checks if the number of rows or columns is too
    big to quickly reformat into slickgrid's json data
    """
    if dataframe.shape[0] > MAX_ROWS or dataframe.shape[1] > MAX_COLS:
        raise TooBigError



