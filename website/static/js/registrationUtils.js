require('css/registrations.css');

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var moment = require('moment');
var URI = require('URIjs');

require('js/koHelpers');

var $osf = require('js/osfHelpers');
var language = require('js/osfLanguage').registrations;

var editorExtensions = require('js/registrationEditorExtensions');

var currentUser = window.contextVars.currentUser || {
    id: null,
    name: 'Anonymous'
};


/**
 * @class Comment
 * Model for storing/editing/deleting comments on form fields
 *
 * @param {Object} data: optional data to instatiate model with
 * @param {User} data.user
 * @param {Date} data.lastModified
 * @param {String} data.value
 *
 * @type User
 * @property {String} id
 * @property {String} name
 **/
function Comment(data) {
    var self = this;

    self.saved = ko.observable(data ? true : false);

    data = data || {};
    self.user = data.user || currentUser;
    self.lastModified = new Date(data.lastModified)|| new Date();
    self.value = ko.observable(data.value || '');
    self.value.subscribe(function() {
        self.lastModified = new Date();
    });

    self.isDeleted = ko.observable(data.isDeleted || false);
    self.isDeleted.subscribe(function(isDeleted) {
      if (isDeleted) {
        self.value('');
      }
    });

    self.seenBy = ko.observableArray([self.user.id] || []);
    self.viewComment = function(user) {
        self.seenBy.push(user.id);
    };

    /**
     * Returns the author as the actual user, not 'You' 
     **/
    self.author = ko.pureComputed(function() {
      return self.user.fullname;
    });

    /**
     * Returns 'You' if the current user is the commenter, else the commenter's name
     */
    self.getAuthor = ko.pureComputed(function() {
      if (self.user.id === currentUser.id) {
        return 'You';
      }
      else {
        return self.user.fullname;
      }
    });

    /**
     * Returns true if the current user is the comment creator
     **/
    self.canDelete = ko.pureComputed(function() {
        return self.user.id === currentUser.id;
    });
    /**
     * Returns true if the comment is saved and the current user is the comment creator
     **/
    self.canEdit = ko.pureComputed(function() {
        return !self.isDeleted() && self.saved() && self.user.id === currentUser.id;
    });
}
Comment.prototype.toggleSaved = function(save) {
    var self = this;

    self.saved(!self.saved());
    if (self.saved()) {
        save();
    }
};
Comment.prototype.delete = function(save) {
    var self = this;

    self.isDeleted(true);
    save();
};
// Let ENTER keypresses add a comment if comment <input> is in focus
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
    if (e.keyCode === 39) {
        $('#editorNextQuestion').click();
    }
    if (e.keyCode === 37) {
        $('#editorPreviousQuestion').click();
    }
});

var validate = function(checks, value) {
    var valid = true;
    $.each(checks, function(i, check) {
        valid = valid && check(value);
    });
    return valid;
};

var validators = {
    string: validate.bind(null, [$osf.not($osf.isBlank)]),
    number: validate.bind(null, [$osf.not($osf.isBlank), $osf.not(isNaN.bind(parseFloat))])
};

/**
 * @class Question
 * Model for schema questions
 *
 * @param {Object} data: optional instantiation values
 * @param {String} data.title
 * @param {String} data.nav: short version of title
 * @param {String} data.type: 'string' | 'number' | 'choose' | 'object'; data type
 * @param {String} data.format: 'text' | 'textarea' | 'list'; format corresponding with data.type
 * @param {String} data.description
 * @param {String} data.help
 * @param {String[]} data.options: array of options for 'choose' types
 * @param {Object[]} data.properties: object of sub-Question properties for 'object' types
 * @param {String} id: unique identifier
 **/
var Question = function(data, id) {
    var self = this;

    self.id = id || -1;

    self.value = ko.observable(data.value || null);
    self.setValue = function(val) {
        self.value(val);
    };

    self.title = data.title || 'Untitled';
    self.nav = data.nav || 'Untitled';
    self.type = data.type || 'string';
    self.format = data.format || 'text';
    self.description = data.description || '';
    self.help = data.help || 'no help text provided';
    self.options = data.options || [];
    self.properties = data.properties || {};
    self.match = data.match || '';

    self.extra = {};

    self.showExample = ko.observable(false);
    self.showUploader = ko.observable(false);

    self.comments = ko.observableArray(
        $.map(data.comments || [], function(comment) {
            return new Comment(comment);
        })
    );
    self.nextComment = ko.observable('');
    /**
     * @returns {Boolean} true if the nextComment <input> is not blank
     **/
    self.allowAddNext = ko.computed(function() {
        return !$osf.isBlank(self.nextComment());
    });

    /**
     * @returns {Boolean} true if the value <input> is not blank
     **/
    self.isComplete = ko.computed(function() {
        return !$osf.isBlank(self.value());
    });

    /**
     * @returns {Boolean} true if the validator matching the question's type returns true,
     * if no validator matches also return true
     **/
    self.valid = ko.computed(function() {
        var value = self.value();
        var isValid = validators[self.type] || function(){ return true; };
        return isValid(value);
    });

    self.init();
};
/**
 * Maps 'object' type Questions's properties to sub-Questions
 **/
Question.prototype.init = function() {
    var self = this;
    if (self.type === 'object') {
        $.each(self.properties, function(prop, field) {
            self.properties[prop] = new Question(field, prop);
        });
    }
};
/**
 * Creates a new comment from the current value of Question.nextComment and clears nextComment
 **/
Question.prototype.addComment = function(save) {
    var self = this;

    var comment = new Comment({
        value: self.nextComment()
    });
    comment.seenBy.push(currentUser.id);
    self.nextComment('');
    self.comments.push(comment);
    save();
};
/**
 * Shows/hides the Question example
 **/
Question.prototype.toggleExample = function(){
    this.showExample(!this.showExample());
};

/**
 * Shows/hides the Question uploader
 **/
Question.prototype.toggleUploader = function(){
    this.showUploader(!this.showUploader());
};

/**
 * Model for MetaSchema instances
 *
 * @param {Object} params: instantiation values
 * @param {String} params.schema_name
 * @param {Integer} params.schema_version
 * @param {String} params.title: display title of schema
 * @param {Schema} params.schema
 *
 * @type Schema
 * @property {String} title
 * @property {Integer} version
 * @property {String} description
 * @property {String[]} fulfills: array of requirements/goals that this schema fulfills
 * @property {Page[]} pages
 *
 * @type Page
 * @property {String} id
 * @property {String} title
 * @property {Question[]} questions
 **/
var MetaSchema = function(params) {
    var self = this;

    self.name = params.schema_name;
    self.version = params.schema_version;
    self.title = params.title || params.schema.title;
    self.schema = params.schema || {};
    self.id = [self.name, self.version].join('_');

    $.each(self.schema.pages, function(i, page) {
        var mapped = {};
        $.each(page.questions, function(qid, question) {
            mapped[qid]  = new Question(question, qid);
        });
        self.schema.pages[i].questions = mapped;
    });
};
/**
 * @returns {Question[]} a flat list of the schema's questions
 **/
MetaSchema.prototype.flatQuestions = function() {
    var self = this;

    var flat = [];

    $.each(self.schema.pages, function(i, page) {
        $.each(page.questions, function(qid, question) {
            flat.push(question);
        });
    });
    return flat;
};

/**
 * @class Draft
 * Model for DraftRegistrations
 *
 * @param {Object} params
 * @param {String} params.pk: primary key of Draft
 * @param {Object} params.registration_schema: data to be passed to MetaSchema constructor
 * @param {Object} params.registration_metadata: saved Draft data
 * @param {User} params.initiator
 * @param {Date} params.initated
 * @param {Date} params.updated
 * @param {Boolean} params.is_pending_review
 * @param {Boolean} params.approved
 * @param {Date} params.updated
 * @param {Object} params.urls
 * @param {String} params.urls.edit
 * @param {String} params.urls.before_register
 * @param {String} params.urls.register
 * @property {Float} completion: percent completion of schema
 **/
var Draft = function(params, metaSchema) {
    var self = this;

    self.pk = params.pk;
    self.metaSchema = metaSchema || new MetaSchema(params.registration_schema);
    self.schema = ko.pureComputed(function() {
        return self.metaSchema.schema;
    });
    self.schemaData = params.registration_metadata || {};

    self.initiator = params.initiator;
    self.initiated = new Date(params.initiated);
    self.updated = new Date(params.updated);

    self.urls = params.urls || {};
    
    // TODO: uncomment to support draft approval states
    //    self.fulfills = params.fulfills || [];
    //    self.isPendingReview = params.flags.isPendingReview || false;
    //    self.requiresApproval = params.config.requiresApproval || false;
    //    self.isApproved = params.flags.isApproved || true;
    //
    //   $.each(params.config || {}, function(key, value) {
    //        self[key] = value;
    //    });
    //    $.each(params.flags || {}, function(key, value) {
    //        self[key] = value;
    //    });
    
    self.completion = ko.computed(function() {
        var total = 0;
        var complete = 0;
        if (self.schemaData) {
            var schema = self.schema();
            $.each(schema.pages, function(i, page) {
                $.each(page.questions, function(qid, question) {
                    var q = self.schemaData[qid];
                    if(q && !$osf.isBlank(q.value)) {
                        complete++;
                    }
                    total++;
                });
            });
	    return Math.ceil(100 * (complete / total));
        }
        return 0;
    });
};
Draft.prototype.beforeRegister = function(data) {
    var self = this;

    $osf.block();

    $.getJSON(self.urls.before_register).then(function(response) {
        var preRegisterWarnings = function() {
            bootbox.confirm(
                {
                    size: 'large',
                    title : language.registerConfirm,
                    message : $osf.joinPrompts(response.prompts),
                    callback: function(result) {
                        if (result) {
                            self.register(data);
                        }
                    }
                }
            );
        };
        var preRegisterErrors = function(confirm, reject) {
            bootbox.confirm(
                $osf.joinPrompts(
                    response.errors, 
                    'Before you continue...'
                ) + '<br /><hr /> ' + language.registerSkipAddons,
                function(result) {
                    if(result) {
                        confirm();
                    }
                }
            );
        };
        
        if (response.errors && response.errors.length) {
            preRegisterErrors(preRegisterWarnings);
        }
        else if (response.prompts && response.prompts.length) {
            preRegisterWarnings();
        } 
        else {
            self.register(data);
        }
    }).always($osf.unblock);
};
Draft.prototype.onRegisterFail =  bootbox.alert.bind(null, {
    title : 'Registration failed',
    message : language.registerFail
});
Draft.prototype.register = function(data) {
    var self = this;

    $osf.block();

    $.ajax({
        url:  self.urls.register,
        type: 'POST',
        data: JSON.stringify(data),
        contentType: 'application/json',
        dataType: 'json'
    }).done(function(response) {
        if (response.status === 'initiated') {            
            window.location.assign(response.urls.registrations);
        }
        else if (response.status === 'error') {
            self.onRegisterFail();
        }
    }).always($osf.unblock).fail(self.onRegisterFail);
};


/**
 * @class RegistrationEditor
 *
 * @param {Object} urls
 * @param {String} urls.update: endpoint to update a draft instance
 * @param {String} editorID: id of editor DOM node
 * @property {ko.observable[Boolean]} readonly
 * @property {ko.observable[Draft]} draft
 * @property {ko.observable[Question]} currentQuestion
 * @property {Object} extensions: mapping of extenstion names to their view models
 *
 * Notes:
 * - The editor can be extended by calling #extendEditor with a type and it's associated ViewModel.
 *   When the context for that type's schema template is built (see #context), that type's ViewModel
 *   is instantiated with the current scope's data as an argument
 **/
var RegistrationEditor = function(urls, editorId) {

    var self = this;

    self.urls = urls;

    self.readonly = ko.observable(false);

    self.draft = ko.observable();

    self.currentQuestion = ko.observable();

    self.currentPages = ko.computed(function() {
        var draft = self.draft();
        if(!draft){
            return [];
        }
        var schema = draft.schema();
        if(!schema) {
            return [];
        }
        return schema.pages;
    });

    self.lastSaveTime = ko.computed(function() {
        if(!self.draft()) {
            return null;
        }
        return self.draft().updated;
    });
    self.lastSaved = ko.computed(function() {
        var t = self.lastSaveTime();
        if (t) {
            return t.toGMTString();
        } else {
            return 'never';
        }
    });

    self.iterObject = $osf.iterObject;

    self.extensions = {
        'osf-upload': editorExtensions.Uploader
    };
};
/**
 * Load draft data into the editor
 *
 * @param {Draft} draft
 **/
RegistrationEditor.prototype.init = function(draft) {
    var self = this;

    self.draft(draft);
    var metaSchema = draft.metaSchema;

    var schemaData = {};
    if(draft) {
        schemaData = draft.schemaData || {};
    }

    var questions = self.flatQuestions();
    $.each(questions, function(i, question) {
        var val = schemaData[question.id];
        if(val) {
            if(question.type === 'object') {
                $.each(question.properties, function(prop, subQuestion) {
                    val = schemaData[question.id][prop];
                    if(val) {
                        subQuestion.value(val.value);
                        subQuestion.comments($.map(val.comments, function(data) {
                            return new Comment(data);
                        }));
                    }
                });
            }
            else {
                question.value(val.value);
                question.comments($.map(val.comments, function(data) {
                    return new Comment(data);
                }));
            }
        }
    });
    self.currentQuestion(questions.shift());
};
/**
 * @returns {Question[]} flat list of the current schema's questions
 **/
RegistrationEditor.prototype.flatQuestions = function() {
    var self = this;

    return self.draft().metaSchema.flatQuestions();
};
/**
 * Creates a template context for editor type subtemplates. Looks for the data type
 * in the extension map, and if found instantiates that type's ViewModel. Otherwise
 * return the bare data Object
 *
 * @param {Object} data: data in current editor template scope
 * @returns {Object|ViewModel}
 **/
RegistrationEditor.prototype.context = function(data) {
    $.extend(data, {
        save: this.save.bind(this),
        readonly: this.readonly
    });

    if (this.extensions[data.type]) {
        return new this.extensions[data.type](data);
    }
    return data;
};
/**
 * Extend the editor's recognized types
 *
 * @param {String} type: unique type
 * @param {Constructor} ViewModel
 **/
RegistrationEditor.prototype.extendEditor = function(type, ViewModel) {
    this.extensions[type] = ViewModel;
};
RegistrationEditor.prototype.viewComments = function() {
  var self = this;

  var comments = self.currentQuestion().comments();
  $.each(comments, function(index, comment) {
    if (comment.seenBy().indexOf(currentUser.id) === -1) {
      comment.seenBy.push(currentUser.id);
    }
  });
};
RegistrationEditor.prototype.getUnseenComments = function(qid) {
    var self = this;

    var question = self.draft().schemaData[qid];
    var comments = question.comments || [];
    for (var key in question) {
        if (key === 'comments') {
            for (var i = 0; i < question[key].length - 1; i++) {
                if (question[key][i].indexOf(currentUser.id) === -1) {
                    comments.push(question[key][i]);
                }
            }
        }
    }
    return comments.length !== 0 ? comments.length : '';
};
RegistrationEditor.prototype.nextQuestion = function() {
    var self = this;

    var currentQuestion = self.currentQuestion();

    var questions = self.flatQuestions();
    var index = $osf.indexOf(questions, function(q) {
        return q.id === currentQuestion.id;
    });
    if(index + 1 === questions.length) {
        self.currentQuestion(questions.shift());
        self.viewComments();
    }
    else {
        self.currentQuestion(questions[index + 1]);
        self.viewComments();
    }
};
RegistrationEditor.prototype.previousQuestion = function() {
    var self = this;

    var currentQuestion = self.currentQuestion();

    var questions = self.flatQuestions();
    var index = $osf.indexOf(questions, function(q) {
        return q.id === currentQuestion.id;
    });
    if(index - 1 < 0){
        self.currentQuestion(questions.pop());
        self.viewComments();
    }
    else {
        self.currentQuestion(questions[index - 1]);
        self.viewComments();
    }
};
RegistrationEditor.prototype.selectPage = function(page) {
    var self = this;

    var firstQuestion = page.questions[Object.keys(page.questions)[0]];
    self.currentQuestion(firstQuestion);
    self.viewComments();
};
RegistrationEditor.prototype.updateData = function(response) {
    var self = this;

    var draft = self.draft();
    draft.pk = response.pk;
    draft.updated = new Date(response.updated);
    self.draft(draft);
};
// TODO: uncomment to allow submit for review
//RegistrationEditor.prototype.submitForReview = function() {
//    var self = this;
//
//    var messages = self.draft().messages;
//    bootbox.confirm(messages.beforeSubmitForApproval, function(result) {
//	if(result) {
//	    $osf.postJSON(self.urls.submit.replace('{draft_pk}', self.draft().pk), {}).then(function() {
//		bootbox.dialog({
//                    closeButton: false,
//		    message: messages.afterSubmitForApproval,
//		    title: 'Pre-Registration Prize Submission',
//		    buttons: {
//                        registrations: {
//                            label: 'Return to registrations page',
//                            className: 'btn-primary pull-right',
//                            callback: function() {
//                                window.location.href = self.draft().urls.registrations;
//                            }
//                        }
//		    }
//		});
//            }).fail($osf.growl.bind(null, 'Error submitting for review', language.submitForReviewFail));
//	}
//    });
//};
RegistrationEditor.prototype.create = function(schemaData) {
    var self = this;

    var metaSchema = self.draft().metaSchema;

    return $osf.postJSON(self.urls.create, {
        schema_name: metaSchema.name,
        schema_version: metaSchema.version,
        schema_data: schemaData
    }).then(self.updateData.bind(self));
};
RegistrationEditor.prototype.submit = function() {
    var self = this;

    var currentNode = window.contextVars.node;
    var currentUser = window.contextVars.currentUser;

    var messages = self.draft().messages;
    bootbox.confirm(messages.beforeSubmitForApproval, function(result) {
        if(result) {
            $osf.postJSON(self.urls.submit.replace('{draft_pk}', self.draft().pk), {
                node: currentNode,
                auth: currentUser
            }).then(function() {
                bootbox.dialog({
                    message: messages.afterSubmitForApproval,
                    title: 'Pre-Registration Prize Submission',
                    buttons: {
                        registrations: {
                            label: 'Return to registrations page',
                            className: 'btn-primary pull-right',
                            callback: function() {
                                window.location.href = self.draft().urls.registrations;
                            }
                        }
                    }
                });
            }).fail($osf.growl.bind(null, 'Error submitting for review', language.submitForReviewFail));
        }
    });
};
RegistrationEditor.prototype.save = function() {
    var self = this;

    var metaSchema = self.draft().metaSchema;
    var schema = metaSchema.schema;
    var data = {};
    $.each(schema.pages, function(i, page) {
        $.each(page.questions, function(qid, question) {
            if(question.type === 'object'){
                var value = {};
                $.each(question.properties, function(prop, subQuestion) {
                    value[prop] = {
                        value: subQuestion.value(),
                        comments: ko.toJS(subQuestion.comments())
                    };
                });
                data[qid] = value;
            }
            else {
                data[qid] = {
                    value: question.value(),
                    comments: ko.toJS(question.comments())
                };
            }
        });
    });

    if (!self.draft().pk){
        return self.create(data);
    }
    $osf.putJSON(self.urls.update.replace('{draft_pk}', self.draft().pk), {
        schema_name: metaSchema.name,
        schema_version: metaSchema.version,
        schema_data: data
    }).then(self.updateData.bind(self));

    return true;
};

var RegistrationManager = function(node, draftsSelector, editorSelector, urls) {
    var self = this;

    self.node = node;
    self.draftsSelector = draftsSelector;
    self.editorSelector = editorSelector;

    self.urls = urls;

    self.schemas = ko.observableArray();
    self.selectedSchema = ko.observable({
        description: ''
    });

    // TODO: convert existing registration UI to frontend impl.
    // self.registrations = ko.observable([]);
    self.drafts = ko.observableArray();

    self.loading = ko.observable(true);

    self.preview = ko.observable(false);

    // bound functions
    self.getDraftRegistrations = $.getJSON.bind(null, self.urls.list);
    self.getSchemas = $.getJSON.bind(null, self.urls.schemas);

    self.sortedDrafts = ko.computed(function() {
        return self.drafts().sort(function(a, b) {
            return a.initiated > b.initiated;
        });
    });

    self.previewSchema = ko.computed(function() {
        var schema = self.selectedSchema();
        return {
            schema: schema.schema,
            readonly: true
        };
    });
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
RegistrationManager.prototype.refresh = function() {
    var self = this;

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
RegistrationManager.prototype.beforeCreateDraft = function() {
    var self = this;

    var node = self.node;

    self.selectedSchema(self.schemas()[0]);
    self.preview(true);
};
RegistrationManager.prototype.maybeWarn = function(draft) {
    var redirect = function() {
        window.location.href = draft.urls.edit;
    };
    // TODO: uncomment this for pre-edit warnings
    //var callback = function(confirmed) {
    //   if(confirmed) {
    //        redirect();
    //    }
    //};
    //if (draft.isApproved) {
    //    bootbox.confirm(language.beforeEditIsApproved, callback);
    //}
    //else if (draft.isPendingReview) {
    //    bootbox.confirm(language.beforeEditIsPendingReview, callback);
    //}
    //else {
    redirect();
    //}
};

module.exports = {
    utilities: {
        validators: validators,
        validate: validate
    },
    Comment: Comment,
    Question: Question,
    MetaSchema: MetaSchema,
    Draft: Draft,
    RegistrationEditor: RegistrationEditor,
    RegistrationManager: RegistrationManager
};
