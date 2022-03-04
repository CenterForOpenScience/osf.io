from nose import tools as nt
from tests.base import OsfTestCase
from website.search import util


class TestSearchUtils(OsfTestCase):

    def test_build_query_with_match_key_and_match_value_valid(self):
        query_body = util.build_query_string('*')
        match_key = 'id'
        match_value = 'f8pzw'
        start = 0
        size = 10
        query_body = {
            'bool': {
                'should': [
                    query_body,
                    {
                        'match_phrase': {
                            match_key: {
                                'query': match_value,
                                'boost': 10.0
                            }
                        }
                    }
                ]
            }
        }

        expectedResult = {
            'query': query_body,
            'from': start,
            'size': size,
        }
        res = util.build_query(start=start, size=size,
                               match_value=match_value, match_key=match_key)
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res, expectedResult)

    def test_build_query_with_match_key_invalid_and_match_value(self):
        query_body = util.build_query_string('*')
        match_key = 1
        match_value = 'f8pzw'
        start = 0
        size = 10

        expectedResult = {
            'query': query_body,
            'from': start,
            'size': size,
        }
        res = util.build_query(start=start, size=size,
                               match_value=match_value, match_key=match_key)
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res, expectedResult)

    def test_build_query_with_match_key_and_match_value_invalid(self):
        query_body = util.build_query_string('*')
        match_key = 1
        match_value = None
        start = 0
        size = 10

        expectedResult = {
            'query': query_body,
            'from': start,
            'size': size,
        }
        res = util.build_query(start=start, size=size,
                               match_value=match_value, match_key=match_key)
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res, expectedResult)

    def test_validate_email_is_not_none(self):
        self.email = 'roger@queen.com'
        result = util.validate_email(self.email)
        nt.assert_equal(result, True)

        result2 = util.validate_email('')
        nt.assert_equal(result2, False)

        result3 = util.validate_email('"joe bloggs"@b.c')
        nt.assert_equal(result3, False)

        result4 = util.validate_email('a@b.c')
        nt.assert_equal(result4, False)

        result5 = util.validate_email('a@b.c@')
        nt.assert_equal(result5, False)

    def test_validate_email_is_none(self):
        self.email = None
        result = util.validate_email(self.email)
        nt.assert_equal(result, False)
