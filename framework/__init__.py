from framework.Flask import send_file, secure_filename, app, route, get, post, redirect, request, url_for, send_from_directory, set_static_folder, Blueprint, render_template, render_template_string, jsonify, abort

##### Template

from framework.Mako import render

###### Session

from framework.Beaker import setPreviousUrl, goback, sessionSet, sessionGet

###### Mongo

from framework.Mongo import db, MongoObject

###### Auth

from framework.Auth import getCurrentUsername, getCurrentUserId, getUser, getCurrentUser, mustBeLoggedIn

##### Form

import Forms
Form = Forms.Form
PasswordField = Forms.PasswordField
BooleanField = Forms.BooleanField
IntegerField = Forms.IntegerField
DateField = Forms.DateField
DateTimeField = Forms.DateTimeField
FileField = Forms.FileField
HiddenField = Forms.HiddenField
RadioField = Forms.RadioField
SelectField = Forms.SelectField
SelectMultipleField = Forms.SelectMultipleField
SubmitField = Forms.SubmitField
TextAreaField = Forms.TextAreaField
TextField = Forms.TextField
validators = Forms.validators
pushErrorsToStatus = Forms.pushErrorsToStatus
MyTextInput = Forms.MyTextInput
FieldList = Forms.FieldList

##### Search

from framework.Search import generateKeywords, search

##### Email
from framework.Email import sendEmail

##### Debug
from framework.Debug import loggerDebug

##### Status

from framework.Status import pushStatusMessage

##### Analytics

from framework.analytics import updateCounters, getBasicCounters

import pytz

def convert_datetime(date, to='US/Eastern'):
    to_zone = pytz.timezone(to)
    date = date.replace(tzinfo=pytz.utc)
    return to_zone.normalize(date.astimezone(to_zone))
