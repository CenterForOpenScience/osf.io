# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # PEP 8 sserts

from website import mails, settings


def test_plain_mail():
    mail = mails.Mail('test', subject='A test email')
    rendered = mail.text(name='World')
    assert_equal(rendered.strip(), 'Hello World')


def test_html_mail():
    mail = mails.Mail('test', subject='A test email')
    rendered = mail.html(name='World')
    assert_equal(rendered.strip(), 'Hello <p>World</p>')


@mock.patch('website.mails.framework_send_email.delay')
def test_send_mail(send_email_delay):
    mails.send_mail('foo@bar.com', mails.TEST, 'plain', name='World')
    assert_true(send_email_delay.called)
    assert_true(send_email_delay.called_with(
        to_addr='foo@bar.com',
        from_addr=settings.FROM_EMAIL,
        mimetype='plain',
        subject=mails.TEST.subject,
        message=mails.TEST.text(name="World")
    ))
