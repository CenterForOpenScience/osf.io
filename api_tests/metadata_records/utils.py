class ExpectedMetadataRecord:
    def __init__(self):
        self.guid = ''
        self.language = ''
        self.resource_type_general = ''
        self.funding_info = []
        self.custom_properties = []

    def assert_for(self, db_record, api_record):
        db_record.refresh_from_db()
        self._assert_all_equal(
            db_record.guid._id,
            api_record['id'],
            expected=self.guid,
        )
        self._assert_all_equal(
            db_record.language,
            api_record['attributes']['language'],
            expected=self.language,
        )
        self._assert_all_equal(
            db_record.resource_type_general,
            api_record['attributes']['resource_type_general'],
            expected=self.resource_type_general,
        )
        self._assert_all_equal(
            db_record.funding_info,
            api_record['attributes']['funders'],
            expected=self.funding_info,
        )
        db_custom_properties = [
            {'property_uri': cp.property_uri, 'value_as_text': cp.value_as_text}
            for cp in db_record.custom_property_set.all()
        ]
        self._assert_all_equal(
            db_custom_properties,
            api_record['attributes']['custom_properties'],
            expected=self.custom_properties,
        )

    def _assert_all_equal(self, *actuals, expected):
        expected = self._freeze(expected)
        for actual in actuals:
            assert self._freeze(actual) == expected

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
