# -*- coding: utf-8 -*-
import pytest

from waffle.models import Flag, Switch
from osf.features import flags, switches
from osf.management.commands.manage_switch_flags import manage_waffle

@pytest.fixture()
def test_switch(monkeypatch):
    test_switches = switches.copy()
    test_switches['TEST_SWITCH'] = 'new_test_switch'
    monkeypatch.setattr('osf.management.commands.manage_switch_flags.switches', test_switches)
    return test_switches

@pytest.fixture()
def test_flag(monkeypatch):
    test_flags = flags.copy()
    test_flags['TEST_FLAG'] = 'new_test_flag'
    monkeypatch.setattr('osf.management.commands.manage_switch_flags.flags', test_flags)
    return test_flags

@pytest.mark.django_db
def test_manage_flags(test_switch, test_flag, monkeypatch):
    manage_waffle()
    assert Flag.objects.filter(name='new_test_flag')
    assert Switch.objects.filter(name='new_test_switch')

    monkeypatch.setattr('osf.management.commands.manage_switch_flags.flags', flags)
    monkeypatch.setattr('osf.management.commands.manage_switch_flags.switches', switches)

    manage_waffle()
    assert Flag.objects.filter(name='new_test_flag')
    assert Switch.objects.filter(name='new_test_switch')

    manage_waffle(True)
    assert not Flag.objects.filter(name='new_test_flag')
    assert not Switch.objects.filter(name='new_test_switch')
