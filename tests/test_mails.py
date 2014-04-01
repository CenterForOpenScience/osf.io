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


@mock.patch('website.mails.framework_send_email')
def test_send_mail(framework_send_email):
    mails.send_mail('foo@bar.com', mails.TEST, 'plain', name='World')
    assert_true(framework_send_email.called)
    assert_true(framework_send_email.called_with(
        to_addr='foo@bar.com',
        from_addr=settings.FROM_EMAIL,
        mimetype='plain',
        subject='A test email to World',
        message=mails.TEST.text(name="World")
    ))
