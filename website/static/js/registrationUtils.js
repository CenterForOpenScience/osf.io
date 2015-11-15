require('css/registrations.css');

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var moment = require('moment');
var History = require('exports?History!history');

require('js/koHelpers');

var $osf = require('js/osfHelpers');
var osfLanguage = require('js/osfLanguage');
var SUPPORT_LINK = osfLanguage.SUPPORT_LINK;
var language = osfLanguage.registrations;

var SaveManager = require('js/saveManager');
var editorExtensions = require('js/registrationEditorExtensions');
var registrationEmbargo = require('js/registrationEmbargo');
// This value should match website.settings.DRAFT_REGISTRATION_APPROVAL_PERIOD
var DRAFT_REGISTRATION_MIN_EMBARGO_DAYS = 10;
var DRAFT_REGISTRATION_MIN_EMBARGO_TIMESTAMP = new Date().getTime() + (
        DRAFT_REGISTRATION_MIN_EMBARGO_DAYS * 24 * 60 * 60 * 1000
);

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
    self.user = data.user || $osf.currentUser();
    self.lastModified = new Date(data.lastModified) || new Date();
    self.value = ko.observable(data.value || '');
    self.value.subscribe(function() {
        self.lastModified = new Date();
    });

    if (data.created) {
        self.created = new Date(data.created);
    }
    else {
        self.created = new Date();
    }

    self.isDeleted = ko.observable(data.isDeleted || false);
    self.isDeleted.subscribe(function(isDeleted) {
        if (isDeleted) {
            self.value('');
        }
    });

    self.seenBy = ko.observableArray([self.user.id]);
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
        if (self.user.id === $osf.currentUser().id) {
            return 'You';
        } else {
            return self.user.fullname;
        }
    });

    /**
     * Returns 'You' if the current user is the commenter, else the commenter's name
     */
    self.getAuthor = ko.pureComputed(function() {
        if (self.user.id === $osf.currentUser().id) {
            return 'You';
        } else {
            return self.user.fullname;
        }
    });

    /**
     * Returns true if the current user is the comment creator
     **/
    self.canDelete = ko.pureComputed(function() {
        return self.user.id === $osf.currentUser().id;
    });
    /**
     * Returns true if the comment is saved and the current user is the comment creator
     **/
    self.canEdit = ko.pureComputed(function() {
        return !self.isDeleted() && self.saved() && self.user.id === $osf.currentUser().id;
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
    if (this.seenBy.indexOf(user.id) === -1) {
        this.seenBy.push(user.id);
    }
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
var Question = function(questionSchema, data) {
    var self = this;

    self.id = questionSchema.qid;

    self.data = data || {};
    if ($.isFunction(self.data.value)) {
        // For subquestions, this could be an observable
        _value = self.data.value();
    } else {
        _value = self.data.value || null;
    }
    self.value = ko.observable(_value);
    self.setValue = function(val) {
        self.value(val);
    };

    self.title = questionSchema.title || 'Untitled';
    self.nav = questionSchema.nav || 'Untitled';
    self.type = questionSchema.type || 'string';
    self.format = questionSchema.format || 'text';
    self.required = questionSchema.required || false;
    self.description = questionSchema.description || '';
    self.help = questionSchema.help;
    self.options = questionSchema.options || [];
    self.properties = questionSchema.properties || {};
    self.match = questionSchema.match || '';

    if (self.required) {
        self.value.extend({
            required: true
        });
    } else {
        self.value.extend({
            required: false
        });
    }
    self.extra = {};

    self.showExample = ko.observable(false);
    self.showUploader = ko.observable(false);

    self.comments = ko.observableArray(
        $.map(self.data.comments || [], function(comment) {
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
    self.isComplete = ko.computed({
        read: function() {
            if (self.type === 'object') {
                var ret = true;
                $.each(self.properties, function(_, subQuestion) {
                    if(subQuestion.type !== 'osf-upload') {
                        if ((subQuestion.value() || '').trim() === '' ) {
                            ret = false;
                            return;
                        }
                    }
                    else {
                        // TODO
                    }
                });
                return ret;
            } else {
                return (self.value() || '').trim() !== '';
            }
        },
        deferEvaluation: true
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
            field.qid = field.id;
            self.properties[prop] = new Question(field, self.data[prop]);
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
    comment.seenBy.push($osf.currentUser().id);
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
 * @class Page
 * A single page within a draft registration
 *
 * @param {Object} data: serialized page from a registration schema
 *
 * @property {ko.observableArray[Question]} questions
 * @property {String} title
 * @property {String} id
 **/
var Page = function(schemaPage, schemaData) {
    var self = this;
    self.questions = ko.observableArray([]);
    self.title = schemaPage.title;
    self.id = schemaPage.id;

    self.active = ko.observable(false);

    schemaData = schemaData || {};
    self.questions = $.map(schemaPage.questions, function(questionSchema) {
        return new Question(questionSchema, schemaData[questionSchema.qid]);
    });

    self.comments = ko.computed(function() {
        var comments = [];
        $.each(self.questions, function(_, question) {
            comments = comments.concat(question.comments());
        });
        comments.sort(function(a, b) {
            return a.created > b.created;
        });
        return comments;
    });

    // TODO: track currentQuestion based on browser focus
    var question = self.questions[0];
    self.nextComment = question.nextComment.bind(question);
    self.allowAddNext = question.allowAddNext.bind(question);
    self.addComment = question.addComment.bind(question);
};

/**
 * @class MetaSchema
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
var MetaSchema = function(params, schemaData) {
    var self = this;

    self.name = params.schema_name;
    self.version = params.schema_version;
    self.title = params.title || params.schema.title;
    self.schema = params.schema || {};
    self.id = params.id;

    // Used for initally selecting a schema
    self._selected = ko.observable(false);

    self.requiresApproval = params.requires_approval || false;
    self.fulfills = params.fulfills || [];
    self.messages = params.messages || {};

    self.consent = params.consent || '';
    self.requiresConsent = params.requires_consent || false;

    self.pages = $.map(self.schema.pages, function(page) {
        return new Page(page, schemaData);
    });
};
/**
 * @returns {Question[]} a flat list of the schema's questions
 **/
MetaSchema.prototype.flatQuestions = function() {
    var self = this;

    var flat = [];
    $.each(self.pages, function(i, page) {
        flat = flat.concat(page.questions);
    });
    return flat;
};

MetaSchema.prototype.askConsent = function() {
    var self = this;

    var ret = $.Deferred();

    var viewModel = {
        message: self.consent,
        consent: ko.observable(false),
        submit: function() {
            $osf.unblock();
            bootbox.hideAll();
            ret.resolve();
        },
        cancel: function() {
            $osf.unblock();
            bootbox.hideAll();
            ret.reject();
        }
    };

    bootbox.dialog({
        size: 'large',
        message: function() {
            ko.renderTemplate('preRegistrationConsent', viewModel, {}, this);
        }
    });

    return ret.promise();
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
    self.schemaData = params.registration_metadata || {};
    self.metaSchema = metaSchema || new MetaSchema(params.registration_schema, self.schemaData);
    self.schema = ko.pureComputed(function() {
        return self.metaSchema.schema;
    });

    self.initiator = params.initiator;
    self.initiated = new Date(params.initiated);
    self.updated = new Date(params.updated);

    self.urls = params.urls || {};

    self.isPendingApproval = params.is_pending_approval;
    self.isApproved = params.is_approved;

    self.requiresApproval = ko.pureComputed(function() {
        return self.metaSchema && self.metaSchema.requiresApproval;
    });
    self.fulfills = ko.pureComputed(function() {
        return self.metaSchema ? self.metaSchema.fulfills : [];
    });

    self.pages = ko.computed(function() {
        return self.metaSchema.pages;
    });

    self.userHasUnseenComment = ko.computed(function() {
        var user = $osf.currentUser();
        var ret = false;
        $.each(self.pages(), function(i, page) {
            $.each(page.comments(), function(idx, comment) {
                if ( comment.seenBy().indexOf(user) === -1 )
                    ret = true;
            });
        });
        return ret;
    });

    self.completion = ko.computed(function() {
        var total = 0;
        var complete = 0;
        $.each(self.metaSchema.flatQuestions(), function(_, question) {
            if (question.isComplete()) {
                complete++;
            }
            total++;
        });
        return Math.ceil(100 * (complete / total));
    });
};
Draft.prototype.preRegisterPrompts = function(response, confirm) {
    var self = this;
    var ViewModel = registrationEmbargo.ViewModel;
    var viewModel = new ViewModel();
    viewModel.canRegister = ko.computed(function() {
        var embargoed = viewModel.showEmbargoDatePicker();
        return (embargoed && viewModel.isEmbargoEndDateValid()) || !embargoed;
    });
    var validation = [];
    if (self.metaSchema.requiresApproval) {
        validation.push({
            validator: function() {
                return viewModel.embargoEndDate().getTime() > DRAFT_REGISTRATION_MIN_EMBARGO_TIMESTAMP;
            },
            message: 'Embargo end date must be at least ' + DRAFT_REGISTRATION_MIN_EMBARGO_DAYS + ' days in the future.'
        });
    }
    validation.push({
        validator: function() {return viewModel.isEmbargoEndDateValid();},
        message: 'Embargo end date must be at least two days in the future.'
    });
    viewModel.pikaday.extend({
        validation: validation
    });
    viewModel.close = function() {
        bootbox.hideAll();
    };
    viewModel.register = function() {
        confirm({
            registrationChoice: viewModel.registrationChoice(),
            embargoEndDate: viewModel.embargoEndDate()
        });
    };
    viewModel.preRegisterPrompts = response.prompts || [];
    bootbox.dialog({
        // TODO: Check button language here
        size: 'large',
        title: language.registerConfirm,
        message: function() {
            ko.renderTemplate('preRegistrationTemplate', viewModel, {}, this);
        }
    });
};
Draft.prototype.preRegisterErrors = function(response, confirm) {
    bootbox.confirm({
        message: $osf.joinPrompts(
            response.errors,
            'Before you continue...'
        ) + '<br />' + language.registerSkipAddons,
        callback: function(result) {
            if (result) {
                confirm();
            }},
        buttons: {
            confirm: {
                label:'Continue with registration',
                className:'btn-primary'
            }}
    });
};
Draft.prototype.askConsent = function() {
    var self = this;

    var ret = $.Deferred();

    var viewModel = {
        message: self.metaSchema.consent,
        consent: ko.observable(false),
        submit: function() {
            $osf.unblock();
            bootbox.hideAll();
            ret.resolve();
        },
        cancel: function() {
            $osf.unblock();
            bootbox.hideAll();
            ret.reject();
        }
    };

    bootbox.dialog({
        size: 'large',
        message: function() {
            ko.renderTemplate('preRegistrationConsent', viewModel, {}, this);
        }
    });

    return ret.promise();
};
Draft.prototype.beforeRegister = function(url) {
    var self = this;

    $osf.block();

    url = url || self.urls.register;

    var request = $.getJSON(self.urls.before_register);
    request.done(function(response) {
        if (response.errors && response.errors.length) {
            self.preRegisterErrors(
                response,
                self.preRegisterPrompts.bind(
                    self,
                    response,
                    self.register.bind(self, url)
                )
            );
        }
        else {
            self.preRegisterPrompts(
                response,
                self.register.bind(self, url)
            );
        }
    }).always($osf.unblock);
    return request;
};
Draft.prototype.registerWithoutReview = function() {
    var self = this;
    bootbox.dialog({
        title: 'Notice',
        message: self.metaSchema.messages.beforeSkipReview,
        buttons: {
            submit: {
                label: 'Continue',
                className: 'btn-primary',
                callback: self.beforeRegister.bind(self, null)
            },
            cancel: {
                label: 'Cancel',
                className: 'btn-default',
                callback: bootbox.hideAll
            }
        }
    });
};
Draft.prototype.onRegisterFail = bootbox.alert.bind(null, {
    title: 'Registration failed',
    message: language.registerFail
});
Draft.prototype.register = function(url, data) {
    var self = this;

    $osf.block();
    var request = $osf.postJSON(url, data);
    request
        .done(function(response) {
            if (response.status === 'initiated') {
                window.location.assign(response.urls.registrations);
            }
        })
        .fail(function() {
            self.onRegisterFail();
        })
        .always($osf.unblock);
    return request;
};
Draft.prototype.submitForReview = function() {
    var self = this;

    var metaSchema = self.metaSchema;
    var messages = metaSchema.messages;
    var beforeSubmitForApprovalMessage = messages.beforeSubmitForApproval || '';
    var afterSubmitForApprovalMessage = messages.afterSubmitForApproval || '';

    var submitForReview = function() {
        bootbox.dialog({
            message: beforeSubmitForApprovalMessage,
            buttons: {
                cancel: {
                    label: 'Cancel',
                    className: 'btn-default',
                    callback: bootbox.hideAll
                },
                ok: {
                    label: 'Continue',
                    className: 'btn-primary',
                    callback: function() {
                        self.beforeRegister(self.urls.submit.replace('{draft_pk}', self.pk));
                    }                    
                }
            }
        });
    };

    if (self.metaSchema.requiresConsent) {
        return self.metaSchema.askConsent()
            .then(function() {
                bootbox.hideAll();
                submitForReview();
            })
            .fail(function() {
                bootbox.hideAll();
            });
    }
};

/**
 * @class RegistrationEditor
 *
 * @param {Object} urls
 * @param {String} urls.update: endpoint to update a draft instance
 * @param {String} editorId: id of editor DOM node
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
    self.showValidation = ko.observable(false);

    self.contributors = ko.observable([]);
    self.getContributors().done(function(data) {
        self.contributors(data);
    });

    self.pages = ko.computed(function () {
        // empty array if self.draft is not set.
        return self.draft() ? self.draft().pages() : [];
    });
    self.currentPage = ko.observable();
    self.currentPage.subscribe(function(currentPage) {
        $.each(self.draft().pages(), function(i, page) {
            page.active(false);
        });
        currentPage.active(true);
        History.replaceState({page: self.pages().indexOf(currentPage)});
    });
    
    self.onLastPage = ko.pureComputed(function() {
        return self.currentPage() === self.pages()[self.pages().length - 1];
    });

    self.serialized = ko.pureComputed(function () {
        // TODO(lyndsysimon): Test this.
        var self = this;
        var data = {};

        $.each(self.pages(), function (_, page) {
            $.each(page.questions, function (_, question) {
                data[question.id] = {
                    value: question.value()
                };
            });
        });

        return {
            schema_name: self.draft().metaSchema.name,
            schema_version: self.draft().metaSchema.version,
            schema_data: data
        };
    }.bind(self));

    // An incrementing dirty flag. The 0 state represents not-dirty.
    // States greater than 0 imply dirty, and incrementing the number
    // allows for reliable mutations of the ko.observable.
    self.dirtyCount = ko.observable(0);
    self.needsSave = ko.computed(function() {
        return self.dirtyCount();
    }).extend({
        rateLimit: 3000,
        method: 'notifyWhenChangesStop'
    });
    self.currentPage.subscribe(function(page) {
        // lazily apply subscriptions to question values
        $.each(page.questions, function(_, question) {
            question.value.subscribe(function() {
                self.dirtyCount(self.dirtyCount() + 1);
            });
        });
    });

    self.canSubmit = ko.computed(function() {
        var canSubmit = true;
        var questions = self.flatQuestions();
        for (var i = 0; i < questions.length; i++) {
            var question = questions[i];
            canSubmit = !question.required || (question.required && question.isComplete());
            if (!canSubmit) {
                break;
            }
        }
        return canSubmit;
    });

    self.iterObject = $osf.iterObject;
    // TODO: better extensions system?
    self.extensions = {
        'osf-upload': editorExtensions.Uploader,
        'osf-author-import': editorExtensions.AuthorImport
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

    self.saveManager = null;
    var schemaData = {};
    if (draft) {
        self.saveManager = new SaveManager(
            self.urls.update.replace('{draft_pk}', draft.pk),
            null, {
                dirty: self.dirtyCount
            }
        );
        schemaData = draft.schemaData || {};
    }

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

    // Set currentPage to the first page
    var pages = self.draft().pages();
    var index = History.getState().data.page || 0;
    if (index > pages.length) {
        index = 0;
    }
    self.currentPage(pages[index]);

    self.needsSave.subscribe(function(dirty) {
        if (dirty) {
            self.save().then(function(last) {
                if (self.dirtyCount() === last){
                    self.dirtyCount(0);
                }
            }.bind(self, self.dirtyCount()));
        }
    });

    self.currentQuestion(self.flatQuestions().shift());
};
/**
 * @returns {Question[]} flat list of the current schema's questions
 **/
RegistrationEditor.prototype.flatQuestions = function() {
    var self = this;
    var draft = self.draft();
    if (draft) {
        return draft.metaSchema.flatQuestions();
    }
    return [];
};
/**
 * Creates a template context for editor type subtemplates. Looks for the data type
 * in the extension map, and if found instantiates that type's ViewModel. Otherwise
 * return the bare data Object
 *
 * @param {Object} data: data in current editor template scope
 * @returns {Object|ViewModel}
 **/
RegistrationEditor.prototype.context = function(data, $root) {
    $.extend(data, {
        save: this.save.bind(this),
        readonly: this.readonly
    });

    if (this.extensions[data.type]) {
        return new this.extensions[data.type](data, $root);
    }
    return data;
};

RegistrationEditor.prototype.toPreview = function () {
    var self = this;
    $osf.block('Saving...');
    self.save().then(function() {
        self.dirtyCount(0);
        window.location.assign(self.draft().urls.register_page);
    });
};

RegistrationEditor.prototype.viewComments = function() {
    var self = this;

    var comments = self.currentQuestion().comments();
    $.each(comments, function(index, comment) {
        if (comment.seenBy().indexOf($osf.currentUser().id) === -1) {
            comment.seenBy.push($osf.currentUser().id);
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
                if (question[key][i].indexOf($osf.currentUser().id) === -1) {
                    comments.push(question[key][i]);
                }
            }
        }
    }
    return comments;
};

/**
 * Check that the Draft is valid before registering
 */
RegistrationEditor.prototype.check = function() {
    var self = this;

    var valid = true;
    ko.utils.arrayMap(self.draft().pages(), function(page) {
        ko.utils.arrayMap(page.questions, function(question) {
            if (question.required && !question.value.isValid()) {
                valid = false;
                // Validation for a question failed
                bootbox.dialog({
                    title: 'Registration Not Complete',
                    message: 'There are errors in your registration. Please double check it and submit again.',
                    buttons: {
                        success: {
                            label: 'Return',
                            className: 'btn-primary',
                            callback: function() {
                                self.showValidation(true);
                            }
                        }
                    }
                });
            }
        });
    });
    if (valid) {
        self.toPreview();
    }
};

RegistrationEditor.prototype.viewComments = function() {
    var self = this;

    var comments = self.currentQuestion().comments();
    $.each(comments, function(index, comment) {
        if (comment.seenBy().indexOf($osf.currentUser().id) === -1) {
            comment.seenBy.push($osf.currentUser().id);
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
                if (question[key][i].indexOf($osf.currentUser().id) === -1) {
                    comments.push(question[key][i]);
                }
            }
        }
    }
    return comments;
};
/**
 * Select a page, selecting the first question on that page
 **/
RegistrationEditor.prototype.selectPage = function(page) {
    var self = this;

    var questions = page.questions;
    var firstQuestion = questions[Object.keys(questions)[0]];
    self.currentQuestion(firstQuestion);
    self.currentPage(page);

    self.viewComments();
};

RegistrationEditor.prototype.nextPage = function () {
    var self = this;
    if (self.onLastPage() || self.pages().length <= 1) {
        return;
    }

    self.currentPage(self.pages()[ self.pages().indexOf(self.currentPage()) + 1 ]);
    window.scrollTo(0,0);
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

RegistrationEditor.prototype.submit = function() {
    var self = this;
    var currentNode = window.contextVars.node;
    var currentUser = $osf.currentUser();
    var messages = self.draft().messages;
    bootbox.confirm(messages.beforeSubmitForApproval, function(result) {
        if (result) {
            var request = $osf.postJSON(self.urls.submit.replace('{draft_pk}', self.draft().pk), {
                node: currentNode,
                auth: currentUser
            });
            request.done(function() {
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
            });
        request.fail($osf.growl.bind(null, 'Error submitting for review', language.submitForReviewFail));
        }
    });
};
/**
 * Create a new draft
 **/
RegistrationEditor.prototype.create = function(schemaData) {
    var self = this;

    var metaSchema = self.draft().metaSchema;

    var request = $osf.postJSON(self.urls.create, {
        schema_name: metaSchema.name,
        schema_version: metaSchema.version,
        schema_data: schemaData
    });
    request.done(function(response) {
        var draft = self.draft();
        draft.pk = response.pk;
        self.draft(draft);
        self.saveManager = new SaveManager(
            self.urls.update.replace('{draft_pk}', draft.pk),
            null,
            {
                dirty: self.dirtyCount
            }
        );
    });
    return request;
};

RegistrationEditor.prototype.putSaveData = function(payload) {
    var self = this;
    return self.saveManager.save(payload)
        .then(self.updateData.bind(self));
};

RegistrationEditor.prototype.saveForLater = function() {
    var self = this;
    $osf.block('Saving...');
    self.save()
        .always($osf.unblock)
        .then(function() {
            self.dirtyCount(0);
            window.location.assign(self.urls.draftRegistrations);
        });
};

/**
 * Save the current Draft
 **/
RegistrationEditor.prototype.save = function() {
    var self = this;
    var metaSchema = self.draft().metaSchema;
    var data = {};
    $.each(metaSchema.pages, function(i, page) {
        $.each(page.questions, function(_, question) {
            var qid = question.id;
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
    var request;
    if (typeof self.draft().pk === 'undefined') {
        request = self.create(self);
    } else {
        request = self.putSaveData({
            schema_name: metaSchema.name,
            schema_version: metaSchema.version,
            schema_data: data
        });
    }
    self.lastSaveRequest = request;
    request.fail(function() {
        $osf.growl('Problem saving draft', 'There was a problem saving this draft. Please try again, and if the problem persists please contact ' + SUPPORT_LINK + '.');
    });
    return request;
};
/**
 * Makes ajax request for a project's contributors
 */
RegistrationEditor.prototype.makeContributorsRequest = function() {
    var self = this;
    var contributorsUrl = window.contextVars.node.urls.api + 'contributors_abbrev/';
    return $.getJSON(contributorsUrl);
};
/**
 * Returns the `user_fullname` of each contributor attached to a node.
 **/
RegistrationEditor.prototype.getContributors = function() {
    var self = this;
    return self.makeContributorsRequest()
        .then(function(data) {
            return $.map(data.contributors, function(c) { return c.user_fullname; });
        }).fail(function() {
            $osf.growl('Could not retrieve contributors.', 'Please refresh the page or ' +
                       'contact <a href="mailto: support@cos.io">support@cos.io</a> if the ' +
                       'problem persists.');
        });
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
var RegistrationManager = function(node, draftsSelector, urls, createButton) {
    var self = this;

    self.node = node;
    self.draftsSelector = draftsSelector;

    self.urls = urls;

    self.schemas = ko.observableArray();
    self.selectedSchema = ko.computed({
        read: function() {
            return self.schemas().filter(function(s) {
                return s._selected();
            })[0];
        },
        write: function(schema) {
            $.each(self.schemas(), function(_, s) {
                s._selected(false);
            });
            schema._selected(true);
        }
    });
    self.selectedSchemaId = ko.computed({
        read: function() {
            return (self.selectedSchema() || {}).id;
        },
        write: function(id) {
            var schemas = self.schemas();
            var schema = schemas.filter(function(s) {
                return s.id === id;
            })[0];
            self.selectedSchema(schema);
        }
    });

    // TODO: convert existing registration UI to frontend impl.
    // self.registrations = ko.observable([]);
    self.drafts = ko.observableArray();
    self.hasDrafts = ko.pureComputed(function() {
        return self.drafts().length > 0;
    });

    self.loading = ko.observable(true);

    self.preview = ko.observable(false);

    // bound functions
    self.getDraftRegistrations = $.getJSON.bind(null, self.urls.list);
    self.getSchemas = $.getJSON.bind(null, self.urls.schemas);

    if (createButton) {
        createButton.on('click', self.createDraftModal.bind(self));
    }
};
RegistrationManager.prototype.init = function() {
    var self = this;

    $osf.applyBindings(self, self.draftsSelector);

    var getSchemas = self.getSchemas();
    getSchemas.done(function(response) {
        self.schemas(
            $.map(response.meta_schemas, function(schema) {
                return new MetaSchema(schema);
            })
        );
    });

    var getDraftRegistrations = self.getDraftRegistrations();
    getDraftRegistrations.done(function(response) {
        self.drafts(
            $.map(response.drafts, function(draft) {
                return new Draft(draft);
            })
        );
    });

    $.when(getSchemas, getDraftRegistrations).done(function() {
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
RegistrationManager.prototype.createDraftModal = function() {
    var self = this;
    if (!self.selectedSchema()){
        self.selectedSchema(self.schemas()[0]);
    }

    bootbox.dialog({
        size: 'large',
        title: 'Register <title>',
        message: function() {
            ko.renderTemplate('createDraftRegistrationModal', self, {}, this);
        },
        buttons: {
            cancel: {
                label: 'Cancel',
                className: 'btn btn-default'
            },
            create: {
                label: 'Create draft',
                className: 'btn btn-primary',
                callback: function(event) {
                    var selectedSchema = self.selectedSchema();
                    if (selectedSchema.requiresConsent) {
                        selectedSchema.askConsent().then(function() {
                            $('#newDraftRegistrationForm').submit();
                        });
                    }
                    else {
                        $('#newDraftRegistrationForm').submit();
                    }
                }
            }
        }
    });
};
/**
 * Redirect to the draft register page
 **/
RegistrationManager.prototype.maybeWarn = function(draft) {
    var redirect = function() {
        window.location.assign(draft.urls.edit);
    };
    var callback = function(confirmed) {
        if (confirmed) {
            redirect();
        }
    };
    if (draft.isApproved) {
        bootbox.confirm(language.beforeEditIsApproved, callback);
    }
    else if (draft.isPendingApproval) {
        bootbox.confirm(language.beforeEditIsPendingReview, callback);
    }
    redirect();
};

module.exports = {
    Comment: Comment,
    Question: Question,
    MetaSchema: MetaSchema,
    Draft: Draft,
    RegistrationEditor: RegistrationEditor,
    RegistrationManager: RegistrationManager
};
