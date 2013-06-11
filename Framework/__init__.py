from Framework.Flask import send_file, secure_filename, app, route, get, post, redirect, request, url_for, send_from_directory, set_static_folder, Blueprint, render_template, render_template_string, jsonify, abort

##### Template

from Framework.Mako import render

###### Session

from Framework.Beaker import setPreviousUrl, goback, sessionSet, sessionGet

###### Mongo

from Framework.Mongo import db, MongoObject

###### Auth

from Framework.Auth import getCurrentUsername, getCurrentUserId, getUser, getCurrentUser, mustBeLoggedIn

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

from Framework.Search import generateKeywords, search

##### Email
from Framework.Email import sendEmail

##### Debug
from Framework.Debug import loggerDebug

##### Status

from Framework.Status import pushStatusMessage

##### Analytics

from Framework.Analytics import updateCounters, getBasicCounters

import pytz

def convert_datetime(date, to='US/Eastern'):
    to_zone = pytz.timezone(to)
    date = date.replace(tzinfo=pytz.utc)
    return to_zone.normalize(date.astimezone(to_zone))
