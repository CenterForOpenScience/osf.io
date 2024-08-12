from datetime import date

import pytest

from osf.metrics.utils import stable_key


class TestStableKey:
    @pytest.mark.parametrize(
        "args, expected_key",
        [
            (
                ["foo"],
                "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
            ),
            (
                [date(1953, 7, 2)],
                "3943be98daa91031ee7d0e0765472ce1b4a50a21f8c6dcd31047d530a50ada93",
            ),
            (
                ["floo", "blar", date(3049, 2, 2)],
                "853cef24d58fa8cd69b20d7dfbcdbd33f20ccda1a14f57e25e43c2533504b64f",
            ),
            (
                [1, 2, 7.3],
                "6ab892f8109fd23b03ab24aebc4e343ed2a058d9a72f750bf90ba051627d233e",
            ),
        ],
    )
    def test_successes(self, args, expected_key):
        actual_key = stable_key(*args)
        assert actual_key == expected_key

    @pytest.mark.parametrize(
        "args",
        [
            [],
            [None],
            ["foo", None],
        ],
    )
    def test_value_errors(self, args):
        with pytest.raises(ValueError):
            stable_key(*args)
