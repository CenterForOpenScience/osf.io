'use strict';

require('css/registrations.css');

require('bootstrap');

var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
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
var RegistrationModal = require('js/registrationModal');

// This value should match website.settings.DRAFT_REGISTRATION_APPROVAL_PERIOD
var DRAFT_REGISTRATION_MIN_EMBARGO_DAYS = 10;
var DRAFT_REGISTRATION_MIN_EMBARGO_TIMESTAMP = new Date().getTime() + (
        DRAFT_REGISTRATION_MIN_EMBARGO_DAYS * 24 * 60 * 60 * 1000
);

var VALIDATORS = {
    required: {
        validator: ko.validation.rules.required.validator,
        message: 'This question is required and unanswered.',
        messagePlural: 'Some required questions are unanswered.'
    }
};
var VALIDATOR_LOOKUP = {};
$.each(VALIDATORS, function(key, value) {
    VALIDATOR_LOOKUP[value.message] = value;
});

/**
 * @class Comment
 * Model for storing/editing/deleting comments on form fields
 *
 * @param {Object} data: optional data to instatiate model with
 * @param {User} data.user
 * @param {Date string} data.lastModified
 * @param {Date string} data.created
 * @param {Boolean} data.isDeleted
 * @param {String} data.value
 *
 * @type User
 * @property {String} id
 * @property {String} fullname
 **/
function Comment(data) {
    var self = this;

    self.saved = ko.observable(data ? true : false);

    data = data || {};
    self.user = data.user || $osf.currentUser();
    self.value = ko.observable(data.value || '');
    self.value.subscribe(function() {
        self.lastModified = new Date();
    });

    self.created = data.created ? new Date(data.created) : new Date();
    self.lastModified = data.lastModified ? new Date(data.lastModified) : new Date();

    self.isDeleted = ko.observable(data.isDeleted || false);
    self.isDeleted.subscribe(function(isDeleted) {
        if (isDeleted) {
            self.value('');
        }
    });

    self.seenBy = ko.observableArray(data.seenBy || [self.user.id]);

    /**
     * Returns true if the current user is the comment owner
     **/
    self.isOwner = ko.pureComputed(function() {
        return self.user.id === $osf.currentUser().id;
    });

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
        if (self.isOwner()) {
            return 'You';
        } else {
            return self.user.fullname;
        }
    });

    /**
     * Returns true if the current user is the comment creator
     **/
    self.canDelete = ko.pureComputed(function() {
        return self.isOwner();
    });

    /**
     * Returns true if the comment is saved and the current user is the comment creator
     **/
    self.canEdit = ko.pureComputed(function() {
        return !self.isDeleted() && self.saved() && self.isOwner();
    });
}
/** Toggle the comment's save state **/
Comment.prototype.toggleSaved = function(save) {
    var self = this;

    if (!self.saved()) {
        // error handling handled implicitly in save
        save().done(self.saved.bind(self, true));
    }
    else {
        self.saved(false);
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
        return true;
    }
    return false;
};

/**
 * @class Question
 * Model for schema questions
 *
 * @param {Object} questionSchema
 * @param {String} questionSchema.title
 * @param {String} questionSchema.nav: short version of title
 * @param {String} questionSchema.type: 'string' | 'number' | 'choose' | 'object'; data type
 * @param {String} questionSchema.format: 'text' | 'textarea' | 'list'; format corresponding with data.type
 * @param {String} questionSchema.description
 * @param {String} questionSchema.help
 * @param {String} questionSchema.required
 * @param {String[]} questionSchema.options: array of options for 'choose' types
 * @param {Object[]} questionSchema.properties: object of sub-Question properties for 'object' types
 * @param {String} questionSchema.match: optional string that must be matched
 * @param {Object} data
 * @param {Any} data.value
 * @param {Array[Object]} data.comments
 * @param {Object} data.extra
 **/
var Question = function(questionSchema, data) {
    var self = this;

    self.data = data || {};

    self.id = questionSchema.qid;
    self.title = questionSchema.title || 'Untitled';
    self.nav = questionSchema.nav || 'Untitled';
    self.type = questionSchema.type || 'string';
    self.format = questionSchema.format || 'text';
    self.required = questionSchema.required || false;
    self.description = questionSchema.description || '';
    self.help = questionSchema.help;
    self.options = questionSchema.options || [];
    self.properties = questionSchema.properties || [];
    self.match = questionSchema.match || '';

    self.extra = ko.observable(self.data.extra || {});
    self.showExample = ko.observable(false);

    self.comments = ko.observableArray(
        $.map(self.data.comments || [], function(comment) {
            return new Comment(comment);
        })
    );
    self.nextComment = ko.observable('');

    var value;
    if (ko.isObservable(self.data.value)) {
        value = self.data.value();
    } else {
        value = self.data.value || null;
    }

    if (self.type === 'choose' && self.format === 'multiselect') {
        if (value) {
            if(!$.isArray(value)) {
                value = [value];
            }
            self.value = ko.observableArray(value);
        }
        else {
            self.value = ko.observableArray([]);
        }
    }
    else if (self.type === 'object') {
        $.each(self.properties, function(index, field) {
            field.qid = field.id;
            var subData = self.data.value ? self.data.value[field.id] : {};
            self.properties[index] = new Question(field, subData);
        });
        self.value = ko.computed({
            read: function() {
                var compositeValue = {};
                $.each(
                    $.map(self.properties, function(prop) {
                        var ret = {};
                        ret[prop.id] = {
                            value: prop.value(),
                            comments: prop.comments(),
                            extra: prop.extra
                        };
                        return ret;
                    }),
                    $.extend.bind(null, compositeValue)
                );
                return compositeValue;
            },
            deferred: true
        });

        self.required = self.required || $osf.any(
            $.map(self.properties, function(prop) {
                return prop.required;
            })
        );
    }
    else {
        self.value = ko.observable(value);
    }

    if (self.required) {
        self.value.extend({
            validation: [
                VALIDATORS.required
            ]
        });
    } else {
        self.value.extend({
            required: false
        });
    }

    /**
     * @returns {Boolean} true if the nextComment <input> is not blank
     **/
    self.allowAddNext = ko.computed(function() {
        return (self.nextComment() || '').trim() !== '';
    });

    /**
     * @returns {Boolean} true if either the question is not required (see logic above) or
     * the question value (or its required children's values) is not empty
     **/
    self.isComplete = ko.computed({
        read: function() {
            if (self.type === 'object') {
                var ret = true;
                $.each(self.properties, function(_, subQuestion) {
                    var value = subQuestion.value();
                    if (subQuestion.required && !(Boolean(value === true || (value && value.length)))) {
                        ret = false;
                        return;
                    }
                });
                return ret;
            } else {
                var value = self.value();
                return !self.required || Boolean(value === true || (value && value.length));
            }
        },
        deferEvaluation: true
    });
};

/**
 * Creates a new comment from the current value of Question.nextComment and clears nextComment
 *
 * @param {function}: save: save function for the current registrationDraft
 **/
Question.prototype.addComment = function(save, page, event) {
    var self = this;

    var comment = new Comment({
        value: self.nextComment()
    });
    comment.seenBy.push($osf.currentUser().id);

    var $comments = $(event.target).closest('.registration-editor-comments');
    $osf.block('Saving...', $comments);
    return save()
        .always($osf.unblock.bind(null, $comments))
        .done(function () {
            self.comments.push(comment);
            self.nextComment('');
        });
};
/**
 * Shows/hides the Question example
 **/
Question.prototype.toggleExample = function() {
    this.showExample(!this.showExample());
};

Question.prototype.validationInfo = function() {
    return ko.validation.group(this, {deep: true})();
};

/**
 * @class Page
 * A single page within a draft registration
 *
 * @param {Object} schemaPage: page representation from a registration schema (see MetaSchema#pages)
 * @param {Object} schemaData: user data to autoload into page, a key/value map of questionId: questionData
 *
 * @property {ko.observableArray[Question]} questions
 * @property {String} title
 * @property {String} id
 * @property {Question[]} questions
 * @property {Question} current Question
 **/
var Page = function(schemaPage, schemaData) {
    var self = this;
    self.id = schemaPage.id;
    self.title = schemaPage.title;
    self.description = schemaPage.description || '';

    self.active = ko.observable(false);

    schemaData = schemaData || {};
    self.questions = $.map(schemaPage.questions, function(questionSchema) {
        return new Question(questionSchema, schemaData[questionSchema.qid]);
    });

    /**
     * Aggregate lists of comments from each question in questions. Sort by 'created'.
     **/
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

    self.validationInfo = ko.computed(function() {
        var errors = $.map(self.questions, function(question) {
            return question.validationInfo();
        }).filter(function(errors) {
            return Boolean(errors);
        });

        var errorSet = ko.utils.arrayGetDistinctValues(errors);
        var finalErrorSet = [];
        $.each(errorSet, function(_, error) {
            if (errors.indexOf(error) !== errors.lastIndexOf(error)) {
                finalErrorSet.push(VALIDATOR_LOOKUP[error].messagePlural);
            }
            else {
                finalErrorSet.push(error);
            }
        });
        return finalErrorSet;
    }, {deferEvaluation: true});

    self.hasValidationInfo = ko.computed(function() {
        return $osf.any(
            self.questions,
            function(question) {
                return question.validationInfo().length > 0;
            }
        );
    }, {deferEvaluation: true});

    // TODO: track currentQuestion based on browser focus
    self.currentQuestion = self.questions[0];
};
Page.prototype.viewComments = function() {
    var self = this;
    var comments = self.comments();
    var viewed = false;
    $.each(comments, function(index, comment) {
        viewed = comment.viewComment($osf.currentUser()) || viewed;
    });
    return viewed;
};
Page.prototype.getUnseenComments = function() {
    var self = this;
    return self.comments().filter(function(comment) {
        return comment.seenBy.indexOf($osf.currentUser().id) === -1;
    });
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
/**
 * @param Boolean pre: consent before beginning or submitting?
 **/
MetaSchema.prototype.askConsent = function(pre) {
    var self = this;

    var ret = $.Deferred();

    if (typeof pre === 'undefined') {
        pre = false;
    }

    var message = (pre ? self.messages.preConsentHeader : self.messages.postConsentHeader) + self.messages.consentBody;

    var viewModel = {
        mustAgree: !pre,
        message: message,
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
        return $osf.any(
            $.map(self.pages(), function(page) {
                return page.getUnseenComments().length > 0;
            })
        );
    });

    self.hasRequiredQuestions = ko.pureComputed(function() {
        return self.metaSchema.flatQuestions().filter(function(q) {
            return q.required;
        }).length > 0;
    });

    self.completion = ko.computed(function() {
        var complete = 0;
        var questions = self.metaSchema.flatQuestions()
                .filter(function(question) {
                    return question.required;
                });
        $.each(questions, function(_, question) {
            if (question.isComplete()) {
                complete++;
            }
        });
        return Math.ceil(100 * (complete / questions.length));
    });
};
Draft.prototype.getUnseenComments = function() {
    var self = this;

    var unseen = [];
    $.each(self.pages(), function(_, page) {
        unseen = unseen.concat(page.getUnseenComments());
    });
    return unseen;
};
Draft.prototype.preRegisterPrompts = function(response, confirm) {
    var self = this;
    var validator = null;
    if (self.metaSchema.requiresApproval) {
        validator = {
            validator: function(value) {
                return (new Date(value)).getTime() > DRAFT_REGISTRATION_MIN_EMBARGO_TIMESTAMP;
            },
            message: 'Embargo end date must be at least ' + DRAFT_REGISTRATION_MIN_EMBARGO_DAYS + ' days in the future.'
        };
    }
    var preRegisterPrompts = response.prompts || [];

    var registrationModal = new RegistrationModal.ViewModel(
        confirm, preRegisterPrompts, validator
    );
    registrationModal.show();
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

Draft.prototype.beforeRegister = function(url) {
    var self = this;

    $osf.block();
    self.checkoutAllFiles();

    url = url || self.urls.register;

    var request = $.getJSON(self.urls.before_register);
    request.done(function(response) {
        $osf.unblock();
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
    }).fail(function(){
        $osf.unblock();
        self.checkinAllFiles();
    });
    return request;
};
Draft.prototype.registerWithoutReview = function() {
    var self = this;
    bootbox.dialog({
        title: 'Notice',
        message: self.metaSchema.messages.beforeSkipReview,
        buttons: {
            cancel: {
                label: 'Cancel',
                className: 'btn-default',
                callback: bootbox.hideAll
            },
            submit: {
                label: 'Continue',
                className: 'btn-warning',
                callback: self.beforeRegister.bind(self, null)
            }
        }
    });
};
Draft.prototype.checkoutAllFiles = function() {
    var self = this;
    var handleFail = function(resp){$osf.growl('Error', 'Unable to check in file');};

    $.each(self.schemaData, function(_, question) {
        if(question.extra.length !== 0) {
            $.each(question.extra, function(_, file) {
                $.ajax({
                    method: 'put',
                    url: window.contextVars.apiV2Prefix + 'files' + file.data.path + '/',
                    beforeSend: $osf.setXHRAuthorization,
                    contentType: 'application/json',
                    dataType: 'json',
                    data: JSON.stringify({
                        data: {
                            id: file.data.path.replace('/', ''),
                            type: 'files',
                            attributes: {
                                checkout: window.contextVars.currentUser.id
                            }
                        }
                    })
                }).fail(handleFail);
            });
        }
    });
};
Draft.prototype.checkinAllFiles = function() {
    var self = this;
    var handleFail = function(resp){$osf.growl('Error', 'Unable to check in file');};

    $.each(self.schemaData, function(_, question) {
        if(question.extra.length !== 0) {
            $.each(question.extra, function(_, file) {
                $.ajax({
                    method: 'put',
                    url: window.contextVars.apiV2Prefix + 'files' + file.data.path + '/',
                    beforeSend: $osf.setXHRAuthorization,
                    contentType: 'application/json',
                    dataType: 'json',
                    data: JSON.stringify({
                        data: {
                            id: file.data.path.replace('/', ''),
                            type: 'files',
                            attributes: {
                                checkout: null
                            }
                        }
                    })
                }).fail(handleFail);
            });
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
            bootbox.alert({
                title: 'Registration failed',
                message: language.registerFail,
                callback: function() {
                    $osf.unblock();
                    if (self.urls.registrations) {
                        window.location.assign(self.urls.registrations);
                    }
                }
            });
        })
        .always(function() {
            $osf.unblock();
        });
    return request;
};
Draft.prototype.submitForReview = function() {
    var self = this;

    var metaSchema = self.metaSchema;

    if (self.metaSchema.requiresConsent) {
        return self.metaSchema.askConsent()
            .always(bootbox.hideAll)
            .then(function() {
                self.beforeRegister(self.urls.submit.replace('{draft_pk}', self.pk));
            });
    }
    else {
        return self.beforeRegister(self.urls.submit.replace('{draft_pk}', self.pk));
    }
};
Draft.prototype.approve = function() {
    var self = this;

    return $osf.dialog(
        'Before you continue...',
        'Are you sure you want to approve this submission? This action is irreversible.',
        'Approve',
        {
            actionButtonClass: 'btn-warning'
        }
    ).done(self.checkinAllFiles);
};
Draft.prototype.reject = function() {
    var self = this;

    return $osf.dialog(
        'Before you continue...',
        'Are you sure you want to reject this submission? This action is irreversible.',
        'Reject',
        {
            actionButtonClass: 'btn-danger'
        }
    ).done(self.checkinAllFiles());
};

/**
 * @class RegistrationEditor
 *
 * @param {Object} urls
 * @param {String} urls.update: endpoint to update a draft instance
 * @param {String} editorId: id of editor DOM node
 * @param {Boolean} preview: enable preview mode-- adds a KO binding handler to allow extensions to define custom preview behavior
 * @property {ko.observable[Boolean]} readonly
 * @property {ko.observable[Draft]} draft
 * @property {ko.observable[Question]} currentQuestion
 * @property {Object} extensions: mapping of extenstion names to their view models
 **/
var RegistrationEditor = function(urls, editorId, preview) {
    var self = this;

    self.urls = urls;

    self.readonly = ko.observable(false);

    self.draft = ko.observable();

    self.currentQuestion = ko.observable();
    self.showValidation = ko.observable(false);

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

    self.onLastPage = ko.computed(function() {
        if(!self.currentPage()) {
            return false;
        }
        var onLastPage = self.currentPage().id === self.pages()[self.pages().length - 1].id;
        if (onLastPage) {
            self.showValidation(true);
        }
        return onLastPage;
    }, {deferEvaluation: true});

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
        // TODO: dispose subscriptions to last page? Probably unncessary.
        $.each(page.questions, function(_, question) {
            question.value.subscribe(function() {
                self.dirtyCount(self.dirtyCount() + 1);
            });
        });
        page.comments.subscribe(function() {
            self.dirtyCount(self.dirtyCount() + 1);
        });
        if(page.viewComments()) {
            self.save();
        }
    });

    self.hasValidationInfo = ko.computed(function() {
        return $osf.any(
            self.pages(),
            function(page) {
                return page.validationInfo().length > 0;
            }
        );
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

    preview = preview || false;
    if (preview) {
        ko.bindingHandlers.previewQuestion = {
            init: function(elem, valueAccessor) {
                var question = valueAccessor();
                var $elem = $(elem);

                if (question.type === 'object') {
                    $elem.append(
                        $.map(question.properties, function(subQuestion) {
                            subQuestion = self.context(subQuestion, self, true);
                            var value;
                            if (self.extensions[subQuestion.type] ) {
                                value = subQuestion.preview();
                            } else {
                                value = $osf.htmlEscape(subQuestion.value() || '');
                            }
                            return $('<p>').append(value);
                        })
                    );
                } else {
                    var value;
                    if (self.extensions[question.type] ) {
                        value = question.preview();
                    } else {
                        value = $osf.htmlEscape(question.value() || '');
                    }
                    $elem.append(value);
                }
            }
        };
    }
};
/**
 * Load draft data into the editor
 *
 * @param {Draft} draft
 **/
RegistrationEditor.prototype.init = function(draft) {
    var self = this;

    self.draft(draft);
    var metaSchema = draft ? draft.metaSchema: null;

    self.saveManager = null;
    if (draft) {
        self.saveManager = new SaveManager(
            self.urls.update.replace('{draft_pk}', draft.pk),
            null, {
                dirty: self.dirtyCount
            }
        );
    }

    self.lastSaveTime = ko.computed(function() {
        if (!self.draft()) {
            return null;
        }
        if (self.draft().updated) {
            return self.draft().updated;
        }
        else {
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
RegistrationEditor.prototype.context = function(data, $root, preview) {
    preview = preview || false;

    $.extend(data, {
        save: this.save.bind(this),
        readonly: this.readonly
    });

    if (this.extensions[data.type]) {
        return new this.extensions[data.type](data, $root, preview);
    }
    return data;
};

RegistrationEditor.prototype.toPreview = function () {
    var self = this;
    $osf.block('Saving...');
    self.save().then(function() {
        self.dirtyCount(0);
        window.location.assign(self.draft().urls.register_page);
    }).always($osf.unblock);
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
        var url = self.urls.submit.replace('{draft_pk}', self.draft().pk);
        if (result) {
            var request = $osf.postJSON(url, {
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
                                window.location.assign(self.draft().urls.registrations);
                                $osf.unblock();
                            }
                        }
                    }
                });
            });
            request.fail(function(xhr, status, error) {
                Raven.captureMessage('Could not submit draft registration', {
                    extra: {
                        url: url,
                        textStatus: status,
                        error: error
                    }
                });
                $osf.growl('Error submitting for review', language.submitForReviewFail);
            });
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
            data[qid] = ko.toJS({
                value: question.value(),
                comments: question.comments(),
                extra: question.extra
            });
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
    request.fail(function(xhr, status, error) {
        Raven.captureMessage('Could not save draft registration', {
            extra: {
                url: self.urls.update.replace('{draft_pk}', self.draft().pk),
                textStatus: status,
                error: error
            }
        });
        $osf.growl('Problem saving draft', 'There was a problem saving this draft. Please try again, and if the problem persists please contact ' + SUPPORT_LINK + '.');
    });
    return request;
};

RegistrationEditor.prototype.approveDraft = function() {
    var self = this;

    var draft = self.draft();
    draft.approve().done(function() {
        $osf.block();
        $.post(self.urls.approve.replace('{draft_pk}', draft.pk))
            .done(function() {
                window.location.assign(self.urls.list);
            }).fail(function() {
                bootbox.alert('There was a problem approving this draft.' + osfLanguage.REFRESH_OR_SUPPORT);
            }).always($osf.unblock);
    });
};
RegistrationEditor.prototype.rejectDraft = function() {
    var self = this;

    var draft = self.draft();
    draft.reject().done(function() {
        $osf.block();
        $.post(self.urls.reject.replace('{draft_pk}', draft.pk))
            .done(function() {
                window.location.assign(self.urls.list);
            }).fail(function() {
                bootbox.alert('There was a problem rejecting this draft.' + osfLanguage.REFRESH_OR_SUPPORT);
            }).always($osf.unblock);
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

    self.loadingSchemas = ko.observable(true);
    self.loadingSchemas.subscribe(function(loading) {
        if (!loading) {
            createButton.removeClass('disabled');
            createButton.text('New registration');
        }
    });
    self.loadingDrafts = ko.observable(true);

    self.preview = ko.observable(false);

    // bound functions
    self.getDraftRegistrations = $.getJSON.bind(null, self.urls.list);
    self.getSchemas = $.getJSON.bind(null, self.urls.schemas);

    if (createButton) {
        createButton.addClass('disabled');
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
        self.loadingSchemas(false);
    });
    getSchemas.fail(function(xhr, status, error) {
        Raven.captureMessage('Could not load registration templates', {
            extra: {
                url: self.urls.schemas,
                textStatus: status,
                error: error
            }
        });
        $osf.growl('Error loading registration templates', language.loadMetaSchemaFail);
    });

    if ($osf.currentUser().isAdmin) {
        var getDraftRegistrations = self.getDraftRegistrations();
        getDraftRegistrations.done(function(response) {
            var drafts = $.map(response.drafts, function(draft) {
                return new Draft(draft);
            });
            drafts.sort(function(a, b) {
                return a.initiated.getTime() < b.initiated.getTime();
            });
            self.drafts(drafts);
            self.loadingDrafts(false);
        });
        getDraftRegistrations.fail(function(xhr, status, error) {
            Raven.captureMessage('Could not load draft registrations', {
                extra: {
                    url: self.urls.list,
                    textStatus: status,
                    error: error
                }
            });
            $osf.growl('Error loading draft registrations', language.loadDraftsFail);
        });

        var urlParams = $osf.urlParams();
        if (urlParams.campaign && urlParams.campaign === 'prereg') {
            $osf.block();
            getSchemas.done(function() {
                var preregSchema = self.schemas().filter(function(schema) {
                    return schema.name === 'Prereg Challenge';
                })[0];
                preregSchema.askConsent(true).then(function() {
                    self.selectedSchema(preregSchema);
                    $('#newDraftRegistrationForm').submit();
                });
            }).always($osf.unblock);
        }
    }
};
/**
 * Confirm and delete a draft registration
 *
 * @param {Draft} draft:
 **/
RegistrationManager.prototype.deleteDraft = function(draft) {
    var self = this;

    var url = self.urls.delete.replace('{draft_pk}', draft.pk);
    bootbox.dialog({
        title: 'Please confirm',
        message: 'Are you sure you want to delete this draft registration?',
        buttons: {
            cancel: {
                label: 'Cancel',
                className: 'btn-default',
                callback: bootbox.hideAll
            },
            submit: {
                label: 'Delete',
                className: 'btn-danger',
                callback: function() {
                    $.ajax({
                        url: url,
                        method: 'DELETE'
                    }).then(function() {
                        self.drafts.remove(function(item) {
                            return item.pk === draft.pk;
                        });
                    }).fail(function(xhr, status, err) {
                        Raven.captureMessage('Could not submit draft registration', {
                            extra: {
                                url: url,
                                textStatus: status,
                                error: err
                            }
                        });
                        $osf.growl('Error deleting draft', language.deleteDraftFail);
                    });
                }
            }
        }
    });
};
/**
 * Show the draft registration preview pane
 **/
RegistrationManager.prototype.createDraftModal = function(selected) {
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
                        selectedSchema.askConsent(true).then(function() {
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
 * Redirect to the draft edit page
 **/
RegistrationManager.prototype.editDraft = function(draft) {
    $osf.block();
    window.location.assign(draft.urls.edit);
    $osf.unblock();
};
RegistrationManager.prototype.previewDraft = function(draft) {
    $osf.block();
    window.location.assign(draft.urls.register_page);
    $osf.unblock();
};


module.exports = {
    Comment: Comment,
    Question: Question,
    Page: Page,
    MetaSchema: MetaSchema,
    Draft: Draft,
    RegistrationEditor: RegistrationEditor,
    RegistrationManager: RegistrationManager
};
