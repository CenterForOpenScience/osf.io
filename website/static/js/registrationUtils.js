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
        self.lastModified = new Date(data.lastModified) || new Date();
        self.value = ko.observable(data.value || '');
        self.value.subscribe(function() {
            self.lastModified = new Date();
        });

        self.created = new Date(data.created) || new Date();

        self.isDeleted = ko.observable(data.isDeleted || false);
        self.isDeleted.subscribe(function(isDeleted) {
            if (isDeleted) {
                self.value('');
            }
        });

        self.seenBy = ko.observableArray([self.user.id] || []);
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
            } else {
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
    /** Toggle the comment's save state **/
Comment.prototype.toggleSaved = function(save) {
    var self = this;

    self.saved(!self.saved());
    if (self.saved()) {
        save();
    }
};
/** Indicate that a comment is deleted **/
Comment.prototype.delete = function(save) {
    var self = this;

    self.isDeleted(true);
    save();
};
/** Indicate that a user has seen a comment **/
Comment.prototype.viewComment = function(user) {
    this.seenBy.push(user.id);
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
 * @param {String} data.required
 * @param {String[]} data.options: array of options for 'choose' types
 * @param {Object[]} data.properties: object of sub-Question properties for 'object' types
 * @param {String} data.match: optional string that must be matched
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
    self.required = data.required || false;
    self.description = data.description || '';
    self.help = data.help;
    self.options = data.options || [];
    self.properties = data.properties || {};
    self.match = data.match || '';

    if (self.required) {
        self.value.extend({
            required: true
        });
    } else {
        self.value.extend({
            required: false
        });
    }
    // A computed to allow rate-limiting save calls
    self.delayedValue = ko.computed(function() {
        return self.value();
    }).extend({ rateLimit: { method: 'notifyWhenChangesStop', timeout: 1000 } });

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
        return (self.nextComment() || '').trim() !== '';
    });

    /**
     * @returns {Boolean} true if the value <input> is not blank
     **/
    self.isComplete = ko.computed(function() {
        return (self.value() || '').trim() !== '';
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
 *
 * @param {function}: save: save function for the current registrationDraft
 **/
Question.prototype.addComment = function(save) {
    var self = this;

    var comment = new Comment({
        value: self.nextComment()
    });
    comment.seenBy.push(currentUser.id);
    self.comments.push(comment);
    self.nextComment('');
    save();
};
/**
 * Shows/hides the Question example
 **/
Question.prototype.toggleExample = function() {
    this.showExample(!this.showExample());
};
/**
 * Shows/hides the Question uploader
 **/
Question.prototype.toggleUploader = function() {
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

    self.requiresApproval = params.requires_approval || false;
    self.fulfills = params.fulfills || [];
    self.messages = params.messages || {};

    var count = 0;
    $.each(self.schema.pages, function(i, page) {
        var mapped = {};
        $.each(page.questions, function(qid, question) {
            // This is necessary now since page.questions is a list
            // This is used to create more unique keys
            var questionId = 'q' + count;
            mapped[questionId]  = new Question(question, questionId);
            count++;
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
 * @param {Date} params.initiated
 * @param {Boolean} params.is_pending_review
 * @param {Boolean} params.is_approved
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


    self.fulfills = params.fulfills || [];
    self.isPendingReview = params.is_pending_review;
    self.isApproved = params.is_approved;

    self.requiresApproval = ko.pureComputed(function() {
        return self.metaSchema && self.metaSchema.requiresApproval;
    });
    self.fulfills = ko.pureComputed(function() {
        return self.metaSchema ? self.metaSchema.fulfills : [];
    });

    self.completion = ko.computed(function() {
        var total = 0;
        var complete = 0;
        if (self.schemaData) {
            var schema = self.schema();
            $.each(schema.pages, function(i, page) {
                $.each(page.questions, function(qid, question) {
                    var q = self.schemaData[qid];
                    if (q && (q.value || '').trim() !== '') {
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
Draft.prototype.preRegisterPrompts = function(response, confirm) {
    var self = this;
    bootbox.confirm({
        size: 'large',
        title: language.registerConfirm,
        message: $osf.joinPrompts(response.prompts),
        callback: function(result) {
            if (result) {
                confirm();
            }
        }
    });
};
Draft.prototype.preRegisterErrors = function(response, confirm) {
    bootbox.confirm(
        $osf.joinPrompts(
            response.errors,
            'Before you continue...'
        ) + '<br />' + language.registerSkipAddons,
        function(result) {
            if (result) {
                confirm();
            }
        }
    );
};
Draft.prototype.beforeRegister = function(data) {
    var self = this;

    $osf.block();

    return $.getJSON(self.urls.before_register).then(function(response) {
        if (response.errors && response.errors.length) {
            self.preRegisterErrors(response, self.preRegisterWarnings);
        } else if (response.prompts && response.prompts.length) {
            self.preRegisterPrompts(response, self.register.bind(self, data));
        } else {
            self.register(data);
        }
    }).always($osf.unblock);
};
Draft.prototype.onRegisterFail = bootbox.alert.bind(null, {
    title: 'Registration failed',
    message: language.registerFail
});
Draft.prototype.register = function(data) {
    var self = this;

    $osf.block();

    $osf.postJSON(self.urls.register, data)
        .done(function(response) {
            if (response.status === 'initiated') {
                window.location.assign(response.urls.registrations);
            } else if (response.status === 'error') {
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
 **/
var RegistrationEditor = function(urls, editorId) {

    var self = this;

    self.urls = urls;

    self.readonly = ko.observable(false);

    self.draft = ko.observable();

    self.currentQuestion = ko.observable();
    // When the currentQuestion changes, save when it's rate-limited value changes
    self.currentQuestion.subscribe(function(question) {
         question.delayedValue.subscribe(self.save.bind(self));
    });
    self.showValidation = ko.observable(false);

    self.currentPages = ko.computed(function() {
        var draft = self.draft();
        if (!draft) {
            return [];
        }
        var schema = draft.schema();
        if (!schema) {
            return [];
        }
        return schema.pages;
    });

    self.lastSaveTime = ko.computed(function() {
        if (!self.draft()) {
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

    self.canRegister = ko.computed(function() {
        var draft = self.draft();
        return draft && draft.isApproved;
    });

    self.iterObject = $osf.iterObject;

    // TODO: better extensions system?
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
    if (draft) {
        schemaData = draft.schemaData || {};
    }

    var questions = self.flatQuestions();
    $.each(questions, function(i, question) {
        var val = schemaData[question.id];
        if (val) {
            if (question.type === 'object') {
                $.each(question.properties, function(prop, subQuestion) {
                    val = schemaData[question.id][prop];
                    if (val) {
                        subQuestion.value(val.value);
                        subQuestion.comments($.map(val.comments || [], function(data) {
                            return new Comment(data);
                        }));
                    }
                });
            } else {
                question.value(val.value);
                question.comments($.map(val.comments || [], function(data) {
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
 * Check that the Draft is valid before registering
 */
RegistrationEditor.prototype.check = function() {
    var self = this;

    var proceed = true;
    $.each(self.flatQuestions(), function(i, question) {
        if (question.required) {
            var valid = question.value.isValid();
            proceed = proceed && valid;
        }
    });
    if (!proceed) {

        bootbox.dialog({
            title: 'Registration Not Complete',
            message: 'There are errors in your registration. Please double check it and submit again.',
            buttons: {
                success: {
                    label: 'Ok',
                    className: 'btn-success',
                    callback: function() {
                        self.showValidation(true);
                    }
                }
            }
        });
    } else {
        window.location = self.draft().urls.register_page;
    }
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
    return comments;
};
/**
 * Load the next question into the editor, wrapping around if needed
 **/
RegistrationEditor.prototype.nextQuestion = function() {
    var self = this;

    var currentQuestion = self.currentQuestion();

    var questions = self.flatQuestions();
    var index = $osf.indexOf(questions, function(q) {
        return q.id === currentQuestion.id;
    });
    if (index + 1 === questions.length) {
        self.currentQuestion(questions.shift());
        self.viewComments();
    } else {
        self.currentQuestion(questions[index + 1]);
        self.viewComments();
    }
};
/**
 * Load the previous question into the editor, wrapping around if needed
 **/
RegistrationEditor.prototype.previousQuestion = function() {
    var self = this;

    var currentQuestion = self.currentQuestion();

    var questions = self.flatQuestions();
    var index = $osf.indexOf(questions, function(q) {
        return q.id === currentQuestion.id;
    });
    if (index - 1 < 0) {
        self.currentQuestion(questions.pop());
        self.viewComments();
    } else {
        self.currentQuestion(questions[index - 1]);
        self.viewComments();
    }
};
/**
 * Select a page, selecting the first question on that page
 **/
RegistrationEditor.prototype.selectPage = function(page) {
    var self = this;

    var firstQuestion = page.questions[Object.keys(page.questions)[0]];
    self.currentQuestion(firstQuestion);
    self.viewComments();
};
/**
 * Update draft primary key and updated time on server response
 **/
RegistrationEditor.prototype.updateData = function(response) {
    var self = this;

    var draft = self.draft();
    draft.pk = response.pk;
    draft.updated = new Date(response.updated);
    self.draft(draft);
};
RegistrationEditor.prototype.submitForReview = function() {
    var self = this;

    var draft = self.draft();
    var metaSchema = draft.metaSchema;
    var messages = metaSchema.messages;
    var beforeSubmitForApprovalMessage = messages.beforeSubmitForApproval || '';
    var afterSubmitForApprovalMessage = messages.afterSubmitForApproval || '';

    bootbox.confirm(beforeSubmitForApprovalMessage, function(confirmed) {
        if (confirmed) {
            $osf.postJSON(self.urls.submit.replace('{draft_pk}', self.draft().pk), {}).then(function() {
                bootbox.dialog({
                    closeButton: false,
                    message: afterSubmitForApprovalMessage,
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
RegistrationEditor.prototype.submit = function() {
    var self = this;
    var currentNode = window.contextVars.node;
    var currentUser = window.contextVars.currentUser;
    var messages = self.draft().messages;
    bootbox.confirm(messages.beforeSubmitForApproval, function(result) {
        if (result) {
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
/**
 * Create a new draft
 **/
RegistrationEditor.prototype.create = function(schemaData) {
    var self = this;

    var metaSchema = self.draft().metaSchema;

    return $osf.postJSON(self.urls.create, {
        schema_name: metaSchema.name,
        schema_version: metaSchema.version,
        schema_data: schemaData
    }).then(self.updateData.bind(self));
};
RegistrationEditor.prototype.putSaveData = function(payload) {
    var self = this;
    $osf.putJSON(self.urls.update.replace('{draft_pk}', self.draft().pk), payload).then(self.updateData.bind(self));
};
/**
 * Save the current Draft
 **/
RegistrationEditor.prototype.save = function() {
    var self = this;
    var metaSchema = self.draft().metaSchema;
    var schema = metaSchema.schema;
    var data = {};
    $.each(schema.pages, function(i, page) {
        $.each(page.questions, function(qid, question) {
            if (question.type === 'object') {
                var value = {};
                $.each(question.properties, function(prop, subQuestion) {
                    value[prop] = {
                        value: subQuestion.value(),
                        comments: ko.toJS(subQuestion.comments())
                    };
                });
                data[qid] = value;
            } else {
                data[qid] = {
                    value: question.value(),
                    comments: ko.toJS(question.comments())
                };
            }
        });
    });

    if (typeof self.draft().pk === 'undefined') {
        self.create(self);
    } else {
        self.putSaveData({
            schema_name: metaSchema.name,
            schema_version: metaSchema.version,
            schema_data: data
        });
    }
    return true;
};

/**
 * @class RegistrationManager
 * Model for listing DraftRegistrations
 *
 * @param {Object} node: optional data to instatiate model with
 * @param {String} draftsSelector: DOM node to bind VM to
 * @param {Object} urls:
 * @param {String} urls.list:
 * @param {String} urls.get:
 * @param {String} urls.delete:
 * @param {String} urls.edit:
 * @param {String} urls.schemas:
 **/
var RegistrationManager = function(node, draftsSelector, urls) {
    var self = this;

    self.node = node;
    self.draftsSelector = draftsSelector;

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
/**
 * Confirm and delete a draft registration
 *
 * @param {Draft} draft:
 **/
RegistrationManager.prototype.deleteDraft = function(draft) {
    var self = this;

    bootbox.confirm('Are you sure you want to delete this draft registration?', function(confirmed) {
        if (confirmed) {
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
/**
 * Show the draft registration preview pane
 **/
RegistrationManager.prototype.beforeCreateDraft = function() {
    var self = this;

    var node = self.node;

    self.selectedSchema(self.schemas()[0]);
    self.preview(true);
};
/**
 * Redirect to the draft register page
 **/
RegistrationManager.prototype.maybeWarn = function(draft) {
    var redirect = function() {
        window.location.href = draft.urls.edit;
    };
    var callback = function(confirmed) {
        if (confirmed) {
            redirect();
        }
    };
    // TODO: Uncomment to support approvals
    // if (draft.isApproved) {
    //     bootbox.confirm(language.beforeEditIsApproved, callback);
    // }
    // else if (draft.isPendingReview) {
    //     bootbox.confirm(language.beforeEditIsPendingReview, callback);
    // }
    // else {
    redirect();
    // }
};

module.exports = {
    Comment: Comment,
    Question: Question,
    MetaSchema: MetaSchema,
    Draft: Draft,
    RegistrationEditor: RegistrationEditor,
    RegistrationManager: RegistrationManager
};
