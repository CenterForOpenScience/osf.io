var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var moment = require('moment');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');

/* global JSONEditor */
require('json-editor'); // TODO webpackify
require('js/json-editor-extensions');

function indexOf(array, searchFn) {
    var len = array.length;
    for(var i = 0; i < len; i++) {
        if(searchFn(array[i])) {
            return i;
        }
    }
    return -1;
}

//######### Commentable ###########
var currentUser = window.contextVars.currentUser || {
    id: null,
    name: 'Anonymous'
};

var Comment = function(parent, data) {
    var self = this;
    
    self.saved = ko.observable(data ? true : false);   
    self.saved.subscribe(function(saved) {
        if(saved) {
            parent.save();
        }
    });

    data = data || {};
    self.user = data.user || currentUser;
    self.lastModified = moment(data.lastModified || new Date());
    self.value = ko.observable(data.value || '');
    self.value.subscribe(function() {
        parent.comments.valueHasMutated();
    });

    self.author = ko.pureComputed(function() {
        if (self.user.id === currentUser.id) {
            return 'You';
        }
        else {
            return self.user.name;
        }
    });
    parent.comments.valueHasMutated();

    self.canDelete = ko.pureComputed(function() {
        return self.user.id === currentUser.id;
    });
    self.canEdit = ko.pureComputed(function() {
        return self.saved() && self.user.id === currentUser.id;
    });
};

$(document).keydown(function(e) {
    if (e.keyCode === 13) {
        $target = $(e.target);
        if ($target.hasClass('registration-editor-comment')) {
            var $button = $target.siblings('span').find('button');
            if(!$button.is(':disabled')) {
                $button.click();
            }
        }
    }
});

/////////////////////

var formattedDate = function(dateString) {
    if (!dateString) {
        return 'never';
    }
    var d = new Date(dateString);
    return moment(dateString).fromNow() + ' (' + d.toGMTString() + ')';
};

var MetaSchema = function(params) {
    this.name = params.schema_name;
    this.version = params.schema_version;
    this.title = params.title || params.schema.title;
    this.schema = params.schema || {};
    this.id = [this.name, this.version].join('_');
};

var Draft = function(params) {
    this.pk = params.pk;
    var metaSchema = params.registration_schema;
    this.schema = metaSchema.schema;
    this.schemaName = metaSchema.name;
    this.schemaVersion = metaSchema.version;
    this.schemaData = params.registration_metadata || {};

    this.initiator = params.initiator;
    this.initiated = params.initiated;
    this.updated = params.updated;
    this.completion = 0.0;
    var total = 0;
    var complete = 0;
    if (this.schemaData) {
        for (var i = 0; i < metaSchema.schema.pages.length; i++) {
            var page = metaSchema.schema.pages[i];
            for (var j = 0; j < page.questions.length; j++) {
                var question = page.questions[j];
                var questionId = Object.keys(question.properties)[0];
                if (this.schemaData[questionId] && this.schemaData[questionId].value) {
                    complete++;
                }
                total++;
            }
        }
        this.completion = 100 * (complete / total);
    }
};

var RegistrationEditor = function(urls, editorId, utils) {

    var self = this;
    self.utils = utils;

    self.urls = urls;
    self.editorId = editorId;
    self.editor = null;

    self.QUESTION_CLASS = 'registration-editor-question';
    self.ACTIVE_CLASS = 'registration-editor-question-current';

    self.DEFAULT_DRAFT = new Draft({
        pk: null,
        registration_schema: new MetaSchema({
            schema: {
                pages: []
            },
            schema_name: '',
            schema_version: ''
        }),
        registration_metadata: {}
    });

    self.draft = ko.observable(self.DEFAULT_DRAFT);

    self.disableSave = ko.pureComputed(function() {
        return !self.draft().schema;
    });

    self.currentPages = ko.computed(function() {
        return self.draft().schema.pages;
    });
    self.pageIndex = ko.observable(0);
    self.questionIndex = ko.observable(0);
    self.isCurrent = function(pageIndex, index) {
        return pageIndex === self.pageIndex() && index === self.questionIndex();
    };

    self.lastSaveTime = ko.observable();
    self.formattedDate = formattedDate;

    self.commentMap = {};

    self.comments = ko.observableArray();
    self.comments.subscribe(function(comments) {
        if(!self.editor || !self.draft().pk) {
            return;
        }
        
        var currentQuestionId = Object.keys(self.editor.getValue())[0];
        self.commentMap[currentQuestionId] = comments;
    });
    self.nextComment = ko.observable('');
    self.allowAddNext = ko.computed(function() {
        return !/^\s*$/.test(self.nextComment());
    });    
};
RegistrationEditor.prototype.init = function(metaSchema, draft) {
    var self = this;

    if (draft) {
        self.draft(draft);
        self.commentMap = {};
        $.each(draft.schemaData, function(prop, value) {
            self.commentMap[prop] = $.map(value.comments, function(comment) {
                return new Comment(self, comment);
            });
        });

        var page = self.draft().schema.pages[0];
        var question = page.questions[0];
        self.updateEditor(page, question);
        var questionId = Object.keys(question.properties)[0];
        self.comments(self.commentMap[questionId] || []);
    } else {
        self.draft(new Draft({
            registration_schema: metaSchema
        }));

        self.updateEditor(metaSchema.schema.pages[0]);
    }

    return self.draft();    
};
RegistrationEditor.prototype.destroy = function() {
    this.comments([]);
    this.draft(this.DEFAULT_DRAFT);
};
// Comments
RegistrationEditor.prototype.addComment = function() {
    var self = this;

    this.comments.push(new Comment(this, {
        value: self.nextComment()
    }));
    
    self.nextComment('');
};
RegistrationEditor.prototype.addComments = function(comments) {
    var self = this;
    self.comments(
        $.map(comments || [], function(data) {
            return new Comment(self, data);
        })
    );
};
///////

RegistrationEditor.prototype.updateData = function(draft) {
    var self = this;

    draft = new Draft(draft);

    self.lastSaveTime(new Date());
    var oldDraft = self.draft() || {};
    var oldData = oldDraft.schemaData || {};
    draft.schemaData = $.extend({}, oldData, draft.schemaData);
    self.draft(draft);
};
RegistrationEditor.prototype.fetchData = function() {
    var self = this;
    var ret = $.Deferred();
    if (!self.draft().pk) {
        ret.resolve();
    }
    $.getJSON(self.urls.get.replace('{draft_pk}', self.draft.pk)).then(ret.resolve);
    return ret;
};
RegistrationEditor.prototype.lastSaved = function() {
    var self = this;

    var t = self.lastSaveTime();
    if (t) {
        return t.toGMTString();
    } else {
        return 'never';
    }
};
RegistrationEditor.prototype.isComplete = function(question) {
    var self = this;

    var draft = self.draft();
    if (!draft || !draft.schemaData) {
        return false;
    }

    var questionId = Object.keys(question.properties)[0];

    if (!draft.schemaData[questionId] || !draft.schemaData[questionId].value) {
        return false;
    }
    return true;
};
RegistrationEditor.prototype.nextPage = function() {
    var self = this;

    var index = $('.' + self.ACTIVE_CLASS).index('.' + self.QUESTION_CLASS);
    $('.' + self.QUESTION_CLASS).eq(index + 1).click();
};
RegistrationEditor.prototype.previousPage = function() {
    var self = this;

    var index = $('.' + self.ACTIVE_CLASS).index('.' + self.QUESTION_CLASS);
    $('.' + self.QUESTION_CLASS).eq(index - 1).click();
};
RegistrationEditor.prototype.updateEditor = function(page, question) {
    var self = this;

    if (!question) {
        question = page.questions[0];        
    }

    // load the data for the first schema and display
    if (self.editor) {
        self.editor.destroy();
    }

    var questionId = Object.keys(question.properties)[0];
    var opts = {
        schema: question,
        theme: 'bootstrap3_OSF',
        disable_collapse: true,
        disable_edit_json: true,
        disable_properties: true,
        no_additional_properties: false
    };
    var startVal = {};
    var value = (self.draft().schemaData[questionId] || {}).value || null;
    if (value) {
        startVal[questionId] = value;
        opts.startval = startVal;
    }
    self.editor = new JSONEditor(document.getElementById(self.editorId), opts);
    self.editor.on('change', function() {
        self.save();
    });
    
    self.comments(self.commentMap[questionId] || []);
};
RegistrationEditor.prototype.selectPage = function(page, event) {
    var self = this;
    self.selectQuestion(page, page.questions[0], event);
};
RegistrationEditor.prototype.selectQuestion = function(page, question, event) {
    var self = this;

    $('.' + self.QUESTION_CLASS).removeClass(self.ACTIVE_CLASS);
    if (event.currentTarget.classList.contains(self.QUESTION_CLASS)) {
        $(event.currentTarget).addClass(self.ACTIVE_CLASS);
    } else {
        $(event.currentTarget).parent().find('.' + self.QUESTION_CLASS).eq(0).addClass(self.ACTIVE_CLASS);
    }
    self.updateEditor(page, question);
    var questionId = Object.keys(question.properties)[0];
    self.comments(self.commentMap[questionId] || []);

    var pages = self.currentPages();       
    var pageIndex = indexOf(pages, function(p)  {
        return p.id === page.id;
    });
    self.pageIndex(pageIndex);
    var questions = page.questions;
    self.questionIndex(indexOf(questions, function(q) {
        return q.id === question.id;
    }));
};
RegistrationEditor.prototype.create = function(schemaData) {
    var self = this;
    return $osf.postJSON(self.urls.create, {
        schema_name: self.draft().schemaName,
        schema_version: self.draft().schemaVersion,
        schema_data: schemaData
    }).then(self.updateData.bind(self)).then(function(){
        self.utils.addDraft(self.draft());
    });
};
RegistrationEditor.prototype.save = function() {    
    var self = this;

    var schemaData = self.editor.getValue();
    var keys = Object.keys(schemaData);
    for (var i = 0; i < keys.length; i++){
        var key = keys[i];
        schemaData[key] = {
            value: schemaData[key] || '',
            comments: $.map(self.commentMap[key] || [], function(comment) {
                return ko.toJS(comment);
            })
        };
    }
    if (!self.draft().pk) {
        return self.create(schemaData);
    }
    return $osf.putJSON(self.urls.update.replace('{draft_pk}', self.draft().pk), {
        schema_name: self.draft().schemaName,
        schema_version: self.draft().schemaVersion,
        schema_data: schemaData
    }).then(self.updateData.bind(self))
        .then(function() {
            self.utils.updateDraft(self.draft());
        });
};

var RegistrationManager = function(node, draftsSelector, editorSelector, controls) {
    var self = this;

    self.node = node;
    self.draftsSelector = draftsSelector;
    self.editorSelector = editorSelector;
    self.controls = controls;

    self.urls = {
        list: node.urls.api + 'draft/',
        get: node.urls.api + 'draft/{draft_pk}/',
        delete: node.urls.api + 'draft/{draft_pk}/',
        schemas: '/api/v1/project/schema/'
    };

    self.schemas = ko.observableArray();
    self.selectedSchema = ko.observable();

    // TODO: convert existing registration UI to frontend impl.
    // self.registrations = ko.observable([]);
    self.drafts = ko.observableArray();
    /*
    self.drafts.subscribe(function(changes) {
        $.each(changes, function(i, change) {
            if(change.status === 'deleted' && self.regEditor) {
                self.regEditor.destroy();
            }
        });
    }, null, 'arrayChange');
     */

    self.loading = ko.observable(true);

    // bound functions
    self.formattedDate = formattedDate;
    self.getDraftRegistrations = $.getJSON.bind(null, self.urls.list);
    self.getSchemas = $.getJSON.bind(null, self.urls.schemas);

    self.sortedDrafts = ko.computed(function() {
        return self.drafts().sort(function(a, b) {
            return a.initiated > b.initiated;
        });
    });
    
    self.controls.showManager();
};
RegistrationManager.prototype.init = function() {
    var self = this;

    $osf.applyBindings(self, self.draftsSelector);

    var getSchemas = self.getSchemas();

    getSchemas.then(function(response) {
        self.schemas(
            $.map(response.meta_schemas, function(schema) {
                return new MetaSchema(schema);
            })
        );
    });

    var getDraftRegistrations = self.getDraftRegistrations();

    getDraftRegistrations.then(function(response) {
        self.drafts(
            $.map(response.drafts, function(draft) {
                return new Draft(draft);
            })
        );
    });

    $.when(getSchemas, getDraftRegistrations).then(function() {
        self.loading(false);
    });
};
RegistrationManager.prototype.launchEditor = function(draft, schema) {
    var self = this;
    var node = self.node;
    
    bootbox.hideAll();
    self.controls.showEditor();

    var newDraft;
    if (self.regEditor) {
        self.regEditor.destroy();
        newDraft = self.regEditor.init(schema, draft);
    }
    else {
        self.regEditor = new RegistrationEditor({
            schemas: '/api/v1/project/schema/',
            create: node.urls.api + 'draft/',
            update: node.urls.api + 'draft/{draft_pk}/',
            get: node.urls.api + 'draft/{draft_pk}/'
        }, 'registrationEditor', {
            addDraft: function(draft) {
                if (!self.drafts().filter(function(d) {
                    return draft.pk === d.pk;
                }).length) {
                    self.drafts.unshift(draft);
                }
            },
            updateDraft: function(draft) {
                self.drafts.remove(function(d) {
                    return d.pk === draft.pk;
                });
                self.drafts.unshift(draft);
            }
        });
        newDraft = self.regEditor.init(schema, draft);    
        $osf.applyBindings(self.regEditor, self.editorSelector);
    }
};
RegistrationManager.prototype.editDraft = function(draft) {
    this.launchEditor(draft, draft.schema);
};
RegistrationManager.prototype.deleteDraft = function(draft) {
    var self = this;
    
    bootbox.confirm('Are you sure you want to delete this draft registration?', function(confirmed) {
        if(confirmed) {
            $.ajax({
                url: self.urls.delete.replace('{draft_pk}', draft.pk),
                method: 'DELETE'
            }).then(function() {
                self.drafts.remove(function(item) {
                    return item.pk === draft.pk;
                });
            });            
        }
    });
};
RegistrationManager.prototype.beforeRegister = function() {
    var self = this;

    var node = self.node;
   
    var VM = {
        title: node.title,
        parentTitle: node.parentTitle,
        parentUrl: node.parentRegisterUrl,
        category: node.category === 'project' ? node.category : 'component',
        schemas: self.schemas,
        selectedSchema: self.selectedSchema,
        cancel: bootbox.hideAll,
        launchEditor: self.launchEditor.bind(self)
    };
    bootbox.dialog({
        title: 'Register ' + node.title,
        message: function() {
            var preRegisterMessage = ko.renderTemplate('preRegisterMessageTemplate', VM, {}, this);
        }
    });
};

module.exports = {
    RegistrationEditor: RegistrationEditor,
    RegistrationManager: RegistrationManager
};
