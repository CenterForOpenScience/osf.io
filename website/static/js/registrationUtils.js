var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var moment = require('moment');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');

/* global JSONEditor */
require('json-editor'); // TODO webpackify
require('js/json-editor-extensions');

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
    this.metaSchema = new MetaSchema(metaSchema);
    this.schema = metaSchema.schema;
    this.schemaName = metaSchema.schema_name;
    this.schemaVersion = metaSchema.schema_version;
    this.schemaData = params.registration_metadata;
    this.initiated = params.initiated;
    this.updated = params.updated;
};

var RegistrationEditor = function(urls, editorId) {

    var self = this;

    self.urls = urls;
    self.editorId = editorId;
    self.editor = null;

    self.QUESTION_CLASS = 'registration-editor-question';
    self.ACTIVE_CLASS = 'registration-editor-question-current';

    self.draft = ko.observable(
        new Draft({
            pk: null,
            registration_schema: {
                schema: {
                    pages: []
                },
                schema_name: '',
                schema_version: ''
            },
            registration_metadata: {}
        })
    );
    self.disableSave = ko.pureComputed(function() {
        return !self.draft().schema;
    });

    self.currentSchema = ko.computed(function() {
        return self.draft().schema;
    });

    self.lastSaveTime = ko.observable();
    self.formattedDate = formattedDate;
};
RegistrationEditor.prototype.init = function(metaSchema, draft) {
    var self = this;

    if (draft) {
        self.updateData(draft);
        self.updateEditor(self.draft().schema.pages[0]);
    } else {
        self.draft(new Draft({
            registration_schema: metaSchema
        }));

        self.updateEditor(metaSchema.schema.pages[0]);
    }

    var needsRefresh = false;
    window.setInterval(self.save.bind(self), 60 * 1000);
};
RegistrationEditor.prototype.selectSchema = function() {
    // TODO preview schema?
};
RegistrationEditor.prototype.updateData = function(draft) {
    var self = this;

    var newDraft = new Draft(draft);
    newDraft.schemaData = $.extend({}, newDraft.schemaData, self.draft().schemaData);
    self.draft(newDraft);
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
    self.editor = new JSONEditor(document.getElementById(self.editorId), {
        schema: question,
        startVal: self.draft().schemaData,
        theme: 'bootstrap3',
        disable_collapse: true,
        disable_edit_json: true,
        disable_properties: true,
        no_additional_properties: false
    });
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
};
RegistrationEditor.prototype.create = function(schemaData) {
    var self = this;

    return $osf.postJSON(self.urls.create, {
        schema_name: self.draft().schemaName,
        schema_version: self.draft().schemaVersion,
        schema_data: schemaData
    }).then(self.updateData.bind(self));
};
RegistrationEditor.prototype.save = function() {
    var self = this;
    var schemaData = self.editor.getValue();
    if (!self.draft().pk) {
        return self.create(schemaData);
    }
    return $osf.putJSON(self.urls.update.replace('{draft_pk}', self.draft().pk), {
        schema_name: self.draft().schemaName,
        schema_version: self.draft().schemaVersion,
        schema_data: schemaData
    }).then(function(response) {
        self.lastSaveTime(new Date());

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

    self.loading = ko.observable(true);

    // bound functions
    self.formattedDate = formattedDate;
    self.getDraftRegistrations = $.getJSON.bind(null, self.urls.list);
    self.getSchemas = $.getJSON.bind(null, self.urls.schemas);

    self.controls.showManager();
};
RegistrationManager.prototype.init = function() {
    var self = this;

    $osf.applyBindings(self, self.draftsSelector);

    var getSchemas = self.getSchemas();

    getSchemas.then(function(response) {
        self.schemas(response.meta_schemas);
    });

    var getDraftRegistrations = self.getDraftRegistrations();

    getDraftRegistrations.then(function(response) {
        self.drafts(response.drafts);
    });

    $.when(getSchemas, getDraftRegistrations).then(function() {
        self.loading(false);
    });
};
RegistrationManager.prototype.launchEditor = function(draft) {
    var self = this;
    var node = self.node;

    bootbox.hideAll();
    self.controls.showEditor();

    var regEditor = new RegistrationEditor({
        schemas: '/api/v1/project/schema/',
        create: node.urls.api + 'draft/',
        update: node.urls.api + 'draft/{draft_pk}/',
        get: node.urls.api + 'draft/{draft_pk}/'
    }, 'registrationEditor');
    var schema = self.selectedSchema();
    regEditor.init(schema, draft);
    $osf.applyBindings(regEditor, self.editorSelector);
    window.editor = regEditor;
};
RegistrationManager.prototype.editDraft = function(draft) {
    this.launchEditor(draft);
};
RegistrationManager.prototype.deleteDraft = function(draft) {
    var self = this;
    $.ajax({
        url: self.urls.delete.replace('{draft_pk}', draft.pk),
        method: 'DELETE'
    }).then(function() {
        self.drafts.remove(function(item) {
            return item.pk === draft.pk;
        });
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
        cancel: function() {
            bootbox.hideAll();
        },
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
