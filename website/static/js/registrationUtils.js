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
var registrationEmbargo = require('js/registrationEmbargo');

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

    if (data.value && typeof(data.value) === 'function') {
        // For subquestions, this could be an observable
        _value = data.value();
    } else {
        _value = data.value || null;
    }
    self.value = ko.observable(_value);
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
var Page = function(schemaPage, data) {
    var self = this;
    self.questions = ko.observableArray([]);
    self.title = schemaPage.title;
    self.id = schemaPage.id;

    $.each(schemaPage.questions, function(id, questionSchema) {
        if (data[id] && data[id].value) {
            questionSchema.value = data[id].value;
        }

        self.questions.push(
            new Question(questionSchema, id)
        );
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

    self.pages = ko.observableArray([]);
    $.each(self.schema().pages, function(id, pageData) {
        self.pages.push(new Page(pageData, self.schemaData));
    });

    self.completion = ko.computed(function() {
        var total = 0;
        var complete = 0;
        if (self.schemaData) {
            var schema = self.schema();
            $.each(self.pages(), function(i, page) {
                $.each(page.questions(), function(qid, question) {

                    if ((question.value() || '').trim()) {
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
        message: function() {
            ko.renderTemplate('preRegistrationTemplate', registrationEmbargo.ViewModel, {}, this);
        },
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
Draft.prototype.onRegisterFail = bootbox.dialog.bind(null, {
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

    self.showValidation = ko.observable(false);

    self.pages = ko.computed(function () {
        // empty array if self.draft is not set.
        return self.draft() ? self.draft().pages() : [];
    });
    self.currentPage = ko.observable();
    self.onLastPage = ko.pureComputed(function() {
        return self.currentPage() === self.pages()[self.pages().length - 1];
    });

    self.serialized = ko.pureComputed(function () {
        // TODO(lyndsysimon): Test this.
        var self = this;
        var data = {};

        $.each(self.pages(), function (_, page) {
            $.each(page.questions(), function (_, question) {
                data[question.id] = {value: question.value()};
            });
        });

        return {
            schema_name: self.draft().metaSchema.name,
            schema_version: self.draft().metaSchema.version,
            schema_data: data
        };
    }.bind(self));

    self.isDirty = ko.pureComputed(function() {
        // TODO(lyndsysimon): Test this.
        var request = self.lastSaveRequest();
        if (request === undefined) {
            // Note that if a save request has not happened, the form is considered dirty.
            return true;
        }
        if (request.payload === undefined) {
            // If the payload is not attached, the .done() handler hasn't been called;
            //      therefore the request has not successfully completed.
            return false;
        }
        return JSON.stringify(request.payload) !== JSON.stringify(self.serialized());
    });

    /* The last autosave request that was sent to the server. */
    self.lastSaveRequest = ko.observable();
    self.lastSaveAge = ko.pureComputed(function () {
        // TODO(lyndsysimon): Test this.
        var request = self.lastSaveRequest();
        if (request === undefined) {
            // not yet saved
            return;
        } else if (request.completedDate === undefined) {
            // request in flight
            return -1;
        } else {
            return (new Date() - request.completedDate);
        }
    });


    self.lastSaved = ko.computed(function() {
        var request = self.lastSaveRequest();
        if (request !== undefined) {
            if (request.completedDate !== undefined) {
                return request.completedDate.toGMTString();
            } else {
                return 'pending';
            }
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

    // Set currentPage to the first page
    self.currentPage(self.draft().pages()[0]);

    self.serialized.subscribe(self.autoSave.bind(self));
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

RegistrationEditor.prototype.toPreview = function () {
    // save the form
    var self = this;
    self.save().done(function () {
        // go to the preview
        window.location = self.draft().urls.register_page;
    });
};

/**
 * Check that the Draft is valid before registering
 */
RegistrationEditor.prototype.check = function() {
    var self = this;

    ko.utils.arrayMap(self.draft().pages(), function(page) {
        ko.utils.arrayMap(page.questions(), function(question) {
            if (question.required && !question.value.isValid()) {
                // Validation for a question failed
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
                return;
            }
            // Validation passed for all applicable questions

            // wait for the last autosave to complete
            if (self.lastSaveRequest()) {
                self.lastSaveRequest().always(function () {
                    self.toPreview();
                });
            } else {
                self.toPreview();
            }
        });
    });
};
/**
 * Select a page, selecting the first question on that page
 **/
RegistrationEditor.prototype.selectPage = function(page) {
    var self = this;

    // var firstQuestion = page.questions[Object.keys(page.questions)[0]];
    self.currentPage(page);
};

RegistrationEditor.prototype.nextPage = function () {
    var self = this;
    if (self.onLastPage() || self.pages().length < 2) {
        return;
    }

    self.currentPage(self.pages()[ self.pages().indexOf(self.currentPage()) + 1 ]);
    window.scrollTo(0,0);
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
    var currentUser = $osf.currentUser();
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
    }).then(function(response) {
        var draft = self.draft();
        draft.pk = response.pk;
        self.draft(draft);
    });
};

/**
 * Autosave the form state, immediately or deferred.
 *
 **/
RegistrationEditor.prototype.autoSave = $osf.throttle(function () {
    // TODO(lyndsysimon): Test this.
    var self = this;
    // Delay between the completion of a save and the next request
    var delay = 5000;

    if (!self.isDirty()) {
        return;
    }

    var hasBeenSaved = function() {
        // bool
        return self.lastSaveRequest() !== undefined;
    };
    var delayRemaining = function () {
        // milliseconds
        return delay - self.lastSaveAge();
    };
    var delaySatisfied = function () {
        // bool
        return delayRemaining() <= 0;
    };

    if(!hasBeenSaved()) {
        self.save().always(function() {
            self.autoSave();
        });
    } else if (delaySatisfied()) {
        self.save().always(function() {
            self.autoSave();
        });
    } else {
        window.setTimeout(self.autoSave.bind(self), delayRemaining());
    }
}, 1000);

/**
 * Save the current Draft
 **/
RegistrationEditor.prototype.save = function() {
    // TODO(lyndsysimon): Test this.
    var self = this;
    var request;

    var payload = self.serialized();
    if (typeof self.draft().pk === 'undefined') {
        // Draft has not yet been assigned a PK; create a new DraftRegistration
        request = $osf.postJSON(self.urls.create, payload);
        request.done(function(data) { self.draft().pk = data.pk; }.bind(self));
    } else {
        // Update an existing DraftRegistration
        var url = self.urls.update.replace('{draft_pk}', self.draft().pk);
        console.log('save: begin');
        request = $osf.putJSON(url, payload);
    }

    self.lastSaveRequest(request);

    request.done(function(data, status, xhr) {
        xhr.completedDate = new Date();
        xhr.payload = payload;
        // Explicitly set the observable to tell KO it changed.
        self.lastSaveRequest(xhr);
        console.log('save: complete');
    });

    return request;
};


RegistrationEditor.prototype.toDraft = function () {
    // save the form
    var self = this;
    self.save().done(function() {
        window.location = self.urls.draftRegistrations;
    });
};

RegistrationEditor.prototype.saveForLater = function () {
    var self = this;

    if (self.lastSaveRequest()) {
        // wait for the last autosave to complete
        self.lastSaveRequest().always(function() {
            self.toDraft();
        });
    } else {
        self.toDraft();
    }

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
    self.selectedSchema = ko.observable();
    self.selectedSchemaId = ko.computed(function() {
        return (self.selectedSchema() || {}).id;
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
                    $('#newDraftRegistrationForm').submit();
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
    Question: Question,
    MetaSchema: MetaSchema,
    Draft: Draft,
    RegistrationEditor: RegistrationEditor,
    RegistrationManager: RegistrationManager
};
