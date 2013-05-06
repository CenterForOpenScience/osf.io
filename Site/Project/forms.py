from Framework import *
from . import *

###############################################################################
# Forms
###############################################################################

class NewProjectForm(Form):
    title    = TextField('Title', [
        validators.Required(message=u'Title is required'),
        validators.Length(min=1, message=u'Title is too short'), 
        validators.Length(max=200, message=u'Title is too long')
    ])
    description    = TextAreaField('Description', [
    ])

class NewNodeForm(Form):
    title    = TextField('Title', [
        validators.Required(message=u'Title is required'),
        validators.Length(min=1, message=u'Title is too short'), 
        validators.Length(max=200, message=u'Title is too long')
    ])
    description     = TextAreaField('Description', [
    ])
    category        = TextAreaField('Category', [
    ])