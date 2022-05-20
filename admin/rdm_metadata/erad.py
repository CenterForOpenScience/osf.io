import csv
from io import StringIO
import logging
import os
from addons.metadata.models import ERadRecordSet


logger = logging.getLogger(__name__)


ERAD_COLUMNS = [
    'KENKYUSHA_NO', 'KENKYUSHA_SHIMEI', 'KENKYUKIKAN_CD', 'KENKYUKIKAN_MEI',
    'HAIBUNKIKAN_CD', 'HAIBUNKIKAN_MEI', 'NENDO', 'SEIDO_CD', 'SEIDO_MEI',
    'JIGYO_CD', 'JIGYO_MEI', 'KADAI_ID', 'KADAI_MEI', 'BUNYA_CD', 'BUNYA_MEI'
]


def validate_record(record_num, row):
    for column in ERAD_COLUMNS:
        if column in row:
            continue
        raise ValueError(f'Column "{column}" not exists (record={record_num})')


def do_populate(filename, content):
    code, _ = os.path.splitext(filename)

    recordset = ERadRecordSet.get_or_create(code=code)

    reader = csv.DictReader(StringIO(content), delimiter='\t', quotechar='"')
    records = 0
    for record_num, row in enumerate(reader):
        validate_record(record_num, row)
        kenkyusha_no = row['KENKYUSHA_NO']
        kadai_id = row['KADAI_ID']
        nendo = int(row['NENDO'])
        record = recordset.get_or_create_record(kenkyusha_no, kadai_id, nendo)
        for key in ERAD_COLUMNS:
            setattr(record, key.lower(), row[key])
        record.save()
        logger.info(f'Row inserted: {kenkyusha_no}, {kadai_id}')
        records += 1
    recordset.save()
    return records
