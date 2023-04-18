from unittest import mock

import rdflib
import pytest

from osf.metadata import gather


def test_badbasket():
    # test non-focus AssertionError
    with pytest.raises(AssertionError):
        gather.Basket(None)
    with pytest.raises(AssertionError):
        gather.Basket('http://hello.example/')


def test_goodbasket():
    BLARG = rdflib.Namespace('https://blarg.example/blarg/')
    focus = gather.Focus(BLARG.item, BLARG.Type)
    mock_gatherers = {
        BLARG.zork: mock.Mock(return_value=(
            (BLARG.item, BLARG.zork, BLARG.zorked),
        )),
        BLARG.bork: mock.Mock(return_value=(
            (BLARG.item, BLARG.bork, BLARG.borked),
            (BLARG.borked, BLARG.lork, BLARG.borklorked),
        )),
        BLARG.hork: mock.Mock(return_value=(
            (BLARG.item, BLARG.hork, BLARG.horked),
        )),
    }
    for predicate, mock_gatherer in mock_gatherers.items():
        gather.er(predicate)(mock_gatherer)
    basket = gather.Basket(focus)
    assert basket.focus == focus
    assert isinstance(basket.gathered_metadata, rdflib.Graph)
    assert len(basket.gathered_metadata) == 1
    assert len(basket._gathertasks_done) == 0
    assert len(basket._known_focus_dict) == 1
    # no repeat gathertasks:
    mock_gatherers[BLARG.zork].assert_not_called()
    mock_gatherers[BLARG.bork].assert_not_called()
    mock_gatherers[BLARG.hork].assert_not_called()
    assert set(basket[BLARG.zork]) == {BLARG.zorked}  # lazy gather
    assert len(basket.gathered_metadata) == 2
    assert len(basket._gathertasks_done) == 1
    mock_gatherers[BLARG.zork].assert_called_once()
    mock_gatherers[BLARG.bork].assert_not_called()
    mock_gatherers[BLARG.hork].assert_not_called()
    assert set(basket[BLARG.bork]) == {BLARG.borked}  # lazy gather
    assert len(basket.gathered_metadata) == 4
    assert len(basket._gathertasks_done) == 2
    mock_gatherers[BLARG.zork].assert_called_once()
    mock_gatherers[BLARG.bork].assert_called_once()
    mock_gatherers[BLARG.hork].assert_not_called()
    assert set(basket[BLARG.bork]) == {BLARG.borked}  # skip repeat gather
    assert len(basket.gathered_metadata) == 4
    assert len(basket._gathertasks_done) == 2
    mock_gatherers[BLARG.zork].assert_called_once()
    mock_gatherers[BLARG.bork].assert_called_once()
    mock_gatherers[BLARG.hork].assert_not_called()
    assert set(basket[BLARG.hork]) == {BLARG.horked}  # lazy gather
    assert len(basket.gathered_metadata) == 5
    assert len(basket._gathertasks_done) == 3
    mock_gatherers[BLARG.zork].assert_called_once()
    mock_gatherers[BLARG.bork].assert_called_once()
    mock_gatherers[BLARG.hork].assert_called_once()

    # __getitem__
    assert set(basket[BLARG.somethin_else]) == set()
    # path:
    assert set(basket[BLARG.bork / BLARG.lork]) == {BLARG.borklorked}
    # explicit subject:
    assert set(basket[BLARG.item:BLARG.zork]) == {BLARG.zorked}
    assert set(basket[BLARG.item:BLARG.lork]) == set()
    assert set(basket[BLARG.borked:BLARG.bork]) == set()
    assert set(basket[BLARG.borked:BLARG.lork]) == {BLARG.borklorked}

    # reset
    basket.reset()
    assert len(basket.gathered_metadata) == 1
    assert len(basket._gathertasks_done) == 0
