'use strict';
var $ = require('jquery');

var $osf = require('js/osfHelpers');
var RegistrationEditor = require('js/registrationEditor');

var node = window.contextVars.node;

if (node.isDraftRegistration) {
    var regEditor = new RegistrationEditor({
        schemas: '/api/v1/schemas/',
        save: node.urls.api + 'schema/',
        data: node.urls.api + 'schema/'
    }, '#registrationEditor');
    $osf.applyBindings(regEditor, '#registrationEditorScope');
    regEditor.init();
}
