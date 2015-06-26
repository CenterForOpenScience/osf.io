var $ = require('jquery');
var ko = require('knockout');

var $osf = require('js/osfHelpers');

var RegistrationEditor = require('js/registrationEditor');

var launchRegistrationEditor = function(node, draft) {
    $osf.fullscreenModal({
            id: 'registrationEditorModal'
        })
        .then(function(modal) {
            var regEditor = new RegistrationEditor({
                schemas: '/api/v1/project/schema/',                
                create: node.urls.api + 'draft/',
                update: node.urls.api + 'draft/{draft_pk}/',
                get: node.urls.api + 'draft/{draft_pk}/'
            }, 'registrationEditor');
            ko.renderTemplate('registrationEditorTemplate', regEditor, {}, modal[0]);
            regEditor.init(draft);
        });
};

var runIntro = function(node) {

};

module.exports = {
    postRegister: function(node) {
        launchRegistrationEditor(node);
        runIntro(node);
    },
    remind: function(node) {

    },
    launchRegistrationEditor: launchRegistrationEditor
};
