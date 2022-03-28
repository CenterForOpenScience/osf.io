import os

here = os.path.split(os.path.abspath(__file__))[0]

def from_csv(fname):
    with open(os.path.join(here, fname), encoding='utf-8-sig') as f:
        return f.read()

REPORT_FORMATS = [
    ('公的資金による研究データのメタデータ登録', 'sample', from_csv('sample_report.csv')),
]
