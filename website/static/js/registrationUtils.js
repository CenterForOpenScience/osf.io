var $ = require('jquery');
var ko = require('knockout');

var $osf = require('js/osfHelpers');

var RegistrationEditor = require('js/registrationEditor');

var launchRegistrationEditor = function(node) {
    $osf.fullscreenModal({
            id: 'registrationEditorModal'
        })
        .then(function(modal) {
            var regEditor = new RegistrationEditor({
                schemas: '/api/v1/schemas/',
                save: node.urls.api + 'schema/',
                data: node.urls.api + 'schema/'
            }, 'registrationEditor');
            ko.renderTemplate('registrationEditorTemplate', regEditor, {}, modal[0]);
            regEditor.init();
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

    }
};
