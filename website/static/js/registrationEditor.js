var $ = require('jquery');
var ko = require('knockout');

var jedit = require('json-editor'); // TODO webpackify
require('js/json-editor-extensions');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');

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
};

var RegistrationEditor = function(urls, editorId) {
    var self = this;

    self.urls = urls;
    self.editorId = editorId;
    self.editor = null;

    self.draft = ko.observable(
        new Draft({
            pk: null,
            registration_schema: {
                schema: {
                    pages: []
                },
                schema_name: '',
                schemaVersion: ''
            },
            registration_metadata: {}
        })
    );
    self.schemas = ko.observable([]);

    self.selectedSchemaName = ko.observable();
    self.selectedSchemaName.subscribe(self.selectSchema.bind(self));

    self.disableSave = ko.pureComputed(function() {
        return !self.draft().schema;
    });
};
RegistrationEditor.prototype.init = function(draft) {
    var self = this;

    if (draft){
        self.updateData(draft);
        self.updateEditor(self.draft().schema.pages[0]);
    }

    self.fetchSchemas().then(self.updateSchemas.bind(self));
};
RegistrationEditor.prototype.selectSchema = function() {
    var self = this;
    if(!self.schemas().length) {
        return;
    }

    var selectedSchemaName = self.selectedSchemaName();

    draft = self.draft();
    draft.schemaName = selectedSchemaName.split('_').slice(0, -1).join('_');
    if (self.schemas().length) {
        var selectedSchema = self.schemas().filter(function(s) {
            return s.id === selectedSchemaName;
        })[0];
        draft.schema = selectedSchema.schema;
        draft.schemaVersion = selectedSchema.version || 1;
    }
    self.draft(draft);

    self.updateEditor(draft.schema.pages[0] || {});
};
RegistrationEditor.prototype.updateSchemas = function(response) {
    var self = this;
    self.schemas(
        $.map(response.meta_schemas, function(ms) {
            return new MetaSchema(ms);
        })
    );
};
RegistrationEditor.prototype.fetchSchemas = function() {
    var self = this;
    return $.getJSON(self.urls.schemas);
};

RegistrationEditor.prototype.updateData = function(draft) {
    var self = this;
    
    var newDraft = new Draft(draft);
    newDraft.schemaData = $.extend({}, newDraft.schemaData, self.draft().schemaData);   
    self.draft(newDraft);

    self.selectedSchemaName(newDraft.metaSchema.id);
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
    self.editor.on('change', function() {
        self.save();
    });
};
RegistrationEditor.prototype.selectPage = function(page, index) {
    var self = this;
    self.updateEditor(page);
};
RegistrationEditor.prototype.selectQuestion = function(page, question) {
    var self = this;
    self.updateEditor(page ,question);
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
        console.log(response);
    });
};
RegistrationEditor.prototype.check = function() {
    var self = this;
    var question = self.editor.schema.nav;
    $('#' + question).attr('class', 'fa fa-check');
};
RegistrationEditor.prototype.uncheck = function() {
    var self = this;
    var question = self.editor.schema.nav;
    $('#' + question).removeClass('fa fa-check');
};
RegistrationEditor.prototype.previous = function() {
    var self = this;
    var currentPageSchema = undefined;
    var currentQuestionID = undefined;
    var previousQuestionID = undefined;
    var previousQuestionSchema = undefined;

    var page;
    for (page in self.schemas._latestValue[0].schema.pages) {
        if (self.schemas._latestValue[0].schema.pages[page].title === self.editor.schema.title) {
            currentPageSchema = self.schemas._latestValue[0].schema.pages[page];
        } 
    } 

    currentQuestionID = self.editor.schema.id;

    if (parseInt(currentQuestionID) === 1) {
        previousQuestionID = currentQuestionID;
    } 
    else if (currentPageSchema.questions[0].id === currentQuestionID) {
        var index = self.schemas._latestValue[0].schema.pages.indexOf(currentPageSchema);
        currentPageSchema = self.schemas._latestValue[0].schema.pages[parseInt(index) - 1];
        previousQuestionID = parseInt(currentQuestionID) - 1;
    }
    else {
        previousQuestionID = parseInt(currentQuestionID) - 1;
    }
    var question;
    for (question in currentPageSchema.questions) {      
        if (parseInt(currentPageSchema.questions[question].id) === parseInt(previousQuestionID)) {
            previousQuestionSchema = currentPageSchema.questions[question];
        }
    }

    self.updateEditor(currentPageSchema, previousQuestionSchema);
};
RegistrationEditor.prototype.next = function() {
    var self = this;
    var currentPageSchema = undefined;
    var currentQuestionID = undefined;
    var previousQuestionID = undefined;
    var previousQuestionSchema = undefined;
    var lastQuestionPage = undefined;

    var page;
    for (page in self.schemas._latestValue[0].schema.pages) {
        if (self.schemas._latestValue[0].schema.pages[page].title === self.editor.schema.title) {
            currentPageSchema = self.schemas._latestValue[0].schema.pages[page];
        } 
    } 

    currentQuestionID = self.editor.schema.id;
    lastQuestionPage = currentPageSchema.questions.length - 1;
    if (parseInt(currentQuestionID) === 22) {
        previousQuestionID = currentQuestionID;
    } 
    else if (currentPageSchema.questions[lastQuestionPage].id === currentQuestionID) {
        var index = self.schemas._latestValue[0].schema.pages.indexOf(currentPageSchema);
        currentPageSchema = self.schemas._latestValue[0].schema.pages[parseInt(index) + 1];
        previousQuestionID = parseInt(currentQuestionID) + 1;
    }
    else {
        previousQuestionID = parseInt(currentQuestionID) + 1;
    }
    var question;
    for (question in currentPageSchema.questions) {      
        if (parseInt(currentPageSchema.questions[question].id) === parseInt(previousQuestionID)) {
            previousQuestionSchema = currentPageSchema.questions[question];
        }
    }

    self.updateEditor(currentPageSchema, previousQuestionSchema);
};

module.exports = RegistrationEditor;
