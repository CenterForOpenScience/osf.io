class ExpectedMetadataRecord:
    def __init__(self):
        self._expected_values = {}

    def __setattr__(self, attrname, attrvalue):
        if attrname.startswith('_'):
            super().__setattr__(attrname, attrvalue)
        else:
            self._expected_values[attrname] = self._freeze(attrvalue)

    def assert_expectations(self, db_record, api_record):
        db_record.refresh_from_db()
        for attrname, expected_value in self._expected_values.items():
            actual_db_value = self._getattr_dbrecord(attrname, db_record)
            actual_api_value = self._getattr_apirecord(attrname, api_record)
            assert actual_db_value == expected_value
            assert actual_api_value == expected_value

    def _getattr_dbrecord(self, attrname, dbrecord):
        if attrname == 'id':
            return dbrecord.guid._id
        return self._freeze(getattr(dbrecord, attrname))

    def _getattr_apirecord(self, attrname, apirecord):
        if attrname == 'id':
            return apirecord['id']
        if attrname == 'funding_info':
            attrname = 'funders'
        return self._freeze(apirecord['attributes'][attrname])

    def _freeze(self, unfrozen):
        frozen = None
        if isinstance(unfrozen, dict):
            frozen = frozenset(
                (k, self._freeze(v))
                for k, v in unfrozen.items()
            )
        elif isinstance(unfrozen, list):
            frozen = frozenset(
                self._freeze(v)
                for v in unfrozen
            )

        if frozen is None:
            return unfrozen
        assert len(frozen) == len(unfrozen), 'unexpected duplicates!'
        return frozen
