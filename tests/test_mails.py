# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # PEP 8 sserts

from website import mails, settings


def test_plain_mail():
    mail = mails.Mail('test', subject='A test email to ${name}')
    rendered = mail.text(name='World')
    assert_equal(rendered.strip(), 'Hello World')
    assert_equal(mail.subject(name='World'), 'A test email to World')


def test_html_mail():
    mail = mails.Mail('test', subject='A test email')
    rendered = mail.html(name='World')
    assert_equal(rendered.strip(), 'Hello <p>World</p>')