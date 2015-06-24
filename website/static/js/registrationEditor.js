var $ = require('jquery');
var ko = require('knockout');

var jedit = require('json-editor'); // TODO webpackify
require('js/json-editor-extensions');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');

require('./registrationEditorExtension.js');

var RegistrationEditor = function(urls, editorId) {
    var self = this;

    self.urls = urls;
    self.editorId = editorId;
    self.editor = null;

    self.defaultOptions = [{
        id: null,
        title: 'Please select a registration form to initiate registration'
    }];
    self.schemas = ko.observable(self.defaultOptions);
    self.selectedSchemaId = ko.observable(null);
    self.selectedSchemaId.subscribe(function() {       
        self.schema(
            self.schemas().filter(function(s) {
                return s.id === self.selectedSchemaId();
            })[0]
        );
        self.updateEditor(self.schema().pages[0]);
    });

    self.schema = ko.observable({});
    self.schema.subscribe(function(schema) {
        self.updateEditor(schema);
    });
    self.schemaData = ko.observable(null);

    self.disableSave = ko.pureComputed(function() {
        return !self.schema();
    });
};
RegistrationEditor.prototype.init = function() {
    var self = this;
    
    $.when(self.fetchData(), self.fetchSchemas()).then(function(data, schemas) {
        data = data[0] || {};
        schemas = schemas[0] || [];
        self.updateData(data);
        self.updateSchemas(schemas);
        if (data.schema_id && schemas){
            self.selectedSchemaId(data.schema_id);
        }
    });
};
RegistrationEditor.prototype.updateSchemas = function(schemas) {
    var self = this;
    self.schemas(self.defaultOptions.concat(schemas));
};
RegistrationEditor.prototype.fetchSchemas = function() {
    var self = this;
    return $.getJSON(self.urls.schemas);
};

RegistrationEditor.prototype.updateData = function(response) {
    var self = this;
    self.schemaData($.extend({}, self.schemaData() || {}, response.schema_data));
};
RegistrationEditor.prototype.fetchData = function() {
    var self = this;
    return $.getJSON(self.urls.data);
};

RegistrationEditor.prototype.updateEditor = function(page) {
    var self = this;

    if (!page) {
        return;
    }
    // load the data for the first schema and display
    if (self.editor) {
        self.editor.destroy();
    }
    self.editor = new JSONEditor(document.getElementById(self.editorId), {
        schema: page,
        startVal: self.schemaData(),
        theme: 'bootstrap3',
        disable_collapse: true,
        disable_edit_json: true,
        disable_properties: true,
        no_additional_properties: true
    });
    self.editor.on('change', function() {
        self.save();
    });
};
RegistrationEditor.prototype.selectPage = function(page) {
    var self = this;
    self.updateEditor(page);
};
RegistrationEditor.prototype.save = function() {
    var self = this;
    var schemaData = self.editor.getValue();

    return $osf.putJSON(self.urls.save, {
        schema_id: self.selectedSchemaId(),
        schema_version: self.schema().version,
        schema_data: schemaData
    }).then(function(response) {
        console.log(response);
    });
};

module.exports = RegistrationEditor;
