from framework.flask import send_file, secure_filename, app, route, get, post,\
    redirect, request, url_for, send_from_directory, set_static_folder, \
    Blueprint, render_template, render_template_string, jsonify, abort

##### Template

from framework.mako import render

###### Celery

from framework.celery import celery

###### Session

from framework.beaker import set_previous_url, goback, session_set, session_get

###### Mongo

from framework.mongo import db, MongoObject

###### Auth

from framework.auth import get_current_username, get_current_user_id, get_user, get_current_user, must_be_logged_in

##### Form

from framework.forms import Form, PasswordField, BooleanField, IntegerField, \
    DateField, DateTimeField, FileField, HiddenField, RadioField, SelectField,\
    SelectMultipleField, SubmitField, TextAreaField, TextField, validators, \
    pushErrorsToStatus, MyTextInput, FieldList

##### Search

from framework.search import generate_keywords, search

##### Email

from framework.Email.email_tasks import send_email

##### Status

from framework.status import push_status_message

##### Analytics

from framework.analytics import update_counters, get_basic_counters

import pytz

def convert_datetime(date, to='US/Eastern'):
    to_zone = pytz.timezone(to)
    date = date.replace(tzinfo=pytz.utc)
    return to_zone.normalize(date.astimezone(to_zone))
