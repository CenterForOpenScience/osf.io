'use strict';
var ko = require('knockout');
var $ = require('jquery');
var bootbox = require('bootbox');
var moment = require('moment');

var $osf = require('js/osfHelpers');
var registrationUtils = require('js/registrationUtils');

var ctx = window.contextVars;
var node = window.contextVars.node;

var preRegisterMessage = function(title, parentTitle, parentUrl, category) {
    // TODO(hrybacki): Remove warning once Retraction/Embargoes goes is merged into production
    if (parentUrl) {
        return 'You are about to register the ' + category + ' <b>' + title +
            '</b> including all components and data within it. This will <b>not</b> register' +
            ' its parent, <b>' + parentTitle + '</b>.' +
            ' If you want to register the parent, please go <a href="' +
            parentUrl + '">here.</a>' +
            // TODO(hrybacki): Remove once Retraction/Embargoes goes is merged into production
            '<hr /><b>Important Note:</b> As early as <u>June 8, 2015</u>, registrations ' +
            'will be made public immediately or can be embargoed for up to four years. ' +
            'There will no longer be the option of creating a permanently private ' +
            'registration. If you register before June 8, 2015 and leave your ' +
            'registration private, then the registration can remain private. After June 8, 2015, ' +
            'if you ever make it public, you will not be able to return it to private. ';
    } else {
        return 'You are about to register <b>' + title + '</b> ' +
            'including all components and data within it. ' +
            'Registration creates a permanent, time-stamped, uneditable version ' +
            'of the project. If you would prefer to register only one particular ' +
            'component, please navigate to that component and then initiate registration.' +
            // TODO(hrybacki): Remove once Retraction/Embargoes goes is merged into production
            '<hr /><b>Important Note:</b> As early as <u>June 8, 2015</u>, registrations ' +
            'will be made public immediately or can be embargoed for up to four years. ' +
            'There will no longer be the option of creating a permanently private ' +
            'registration. If you register before June 8, 2015 and leave your ' +
            'registration private, then the registration can remain private. After June 8, 2015, ' +
            'if you ever make it public, you will not be able to return it to private.';
    }
};

var RegistrationManager = function(urls) {
    var self = this;

    self.urls = urls;

    // TODO: convert existing registration UI to frontend impl.
    // self.registrations = ko.observable([]);
    self.drafts = ko.observableArray();
};
RegistrationManager.prototype.getRegistrations = function() {
    var self = this;

    return $.getJSON(self.urls.list);
};
RegistrationManager.prototype.init = function() {
    var self = this;
    
    self.getRegistrations().then(function(response) {
        // self.registrations(response.registrations);
        self.drafts(response.drafts);
    });
};
RegistrationManager.prototype.formatDate = function(dateString){
    return moment(dateString).toNow();
};
RegistrationManager.prototype.editDraft = function(draft) {
    registrationUtils.launchRegistrationEditor(node, draft);
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


$(document).ready(function() {
    var draftManager = new RegistrationManager({
        list: node.urls.api + 'draft/',
        get: node.urls.api + 'draft/{draft_pk}/',
        delete: node.urls.api + 'draft/{draft_pk}/'
    });
    draftManager.init();
    $osf.applyBindings(draftManager, '#draftRegistrationScope');


    $('#registerNode').click(function(event) {
        var node = window.contextVars.node;
        var target = event.currentTarget.href;

        event.preventDefault();
        var title = node.title;
        var parentTitle = node.parentTitle;
        var parentRegisterUrl = node.parentRegisterUrl;
        var category = node.category;
        var bootboxTitle = 'Register ' + title;
        if (node.category !== 'project') {
            category = 'component';
        }

        bootbox.confirm({
            title: bootboxTitle,
            message: preRegisterMessage(title, parentTitle, parentRegisterUrl, category),
            callback: function(confirmed) {
                if (confirmed) {
                    registrationUtils.postRegister(node);
                }
            }
        });
    });
});
