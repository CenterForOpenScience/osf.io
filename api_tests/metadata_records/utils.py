class ExpectedMetadataRecord:
    def __init__(self):
        self._expected_values = {}

    def __setattr__(self, attrname, attrvalue):
        if attrname.startswith("_"):
            super().__setattr__(attrname, attrvalue)
        else:
            self._expected_values[attrname] = attrvalue

    def __getattr__(self, attrname):
        return self._expected_values[attrname]

    def assert_expectations(self, db_record, api_record):
        db_record.refresh_from_db()
        for attrname, expected_value in self._expected_values.items():
            actual_db_value = self._getattr_dbrecord(attrname, db_record)
            assert actual_db_value == expected_value
            if api_record is not None:
                actual_api_value = self._getattr_apirecord(
                    attrname, api_record
                )
                assert actual_api_value == expected_value

    def _getattr_dbrecord(self, attrname, dbrecord):
        if attrname == "id":
            return dbrecord.guid._id
        return getattr(dbrecord, attrname)

    def _getattr_apirecord(self, attrname, apirecord):
        if attrname == "id":
            return apirecord["id"]
        if attrname == "funding_info":
            attrname = "funders"
        return apirecord["attributes"][attrname]
