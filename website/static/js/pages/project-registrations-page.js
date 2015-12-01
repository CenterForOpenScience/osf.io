'use strict';
require('css/registrations.css');

var ko = require('knockout');
var $ = require('jquery');

var $osf = require('js/osfHelpers');
var RegistrationManager = require('js/registrationUtils').RegistrationManager;

var ctx = window.contextVars;
var node = window.contextVars.node;

$(document).ready(function() {

    $('#registrationsTabs').tab();
    $('#registrationsTabs a').click(function (e) {
        e.preventDefault();
        $(this).tab('show');
    });

    var urlParams = $osf.urlParams();
    var tab = urlParams.tab;
    if (tab) {
        if(tab === 'drafts') {
            $('#draftsControl').tab('show');
        }
        else {
            $('#registrationsControl').tab('show');
        }
    }

    var draftManager = new RegistrationManager(node, '#draftRegistrationsScope', {
        list: node.urls.api + 'drafts/',
        submit: node.urls.api + 'draft/{draft_pk}/submit/',
        delete: node.urls.api + 'drafts/{draft_pk}/',
        schemas: '/api/v1/project/drafts/schemas/',
        edit: node.urls.web + 'drafts/{draft_pk}/',
        create: node.urls.web + 'registrations/'
    }, $('#registerNode'));
    draftManager.init();
});
