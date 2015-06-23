/**
* Controls the actions in the project header (make public/private, watch button,
* forking, etc.)
*/
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var Raven = require('raven-js');
require('bootstrap-editable');
require('knockout.punches');
ko.punches.enableAll();

var osfHelpers = require('js/osfHelpers');
var NodeActions = require('js/project.js');
var iconmap = require('js/iconmap');

// Modal language
var MESSAGES = {
    makeProjectPublicWarning: 'Once a project is made public, there is no way to guarantee that ' +
                        'access to the data it contains can be completely prevented. Users ' +
                        'should assume that once a project is made public, it will always ' +
                        'be public. <b>Review your project for sensitive or restricted information before making it public</b>. Are you absolutely sure you would like to continue?',

    makeProjectPrivateWarning: 'Making a project private will prevent users from viewing it on this site, ' +
                        'but will have no impact on external sites, including Google\'s cache. ' +
                        'Would you like to continue?',

    makeComponentPublicWarning: 'Once a component is made public, there is no way to guarantee that ' +
                        'access to the data it contains can be completely prevented. Users ' +
                        'should assume that one a component is made public, it will always ' +
                        'be public. The rest of the project, including other components, ' +
                        'will not be made public. <b>Review your component for sensitive or restricted information before making it public</b>. Are you absolutely sure you would like to continue?',

    makeComponentPrivateWarning: 'Making a component private will prevent users from viewing it on this site, ' +
                        'but will have no impact on external sites, including Google\'s cache. ' +
                        'Would you like to continue?',
    // TODO(hrybacki): Remove once Retraction/Embargoes goes is merged into production
    makeRegistrationPublicWarning: '<b>Important Note:</b> As early as <u>June 8, 2015</u>, new registrations ' +
                        'will be made public immediately or can be embargoed for up to four years. There ' +
                        'will no longer be the option of creating a permanently private registration. This ' +
                        'registration occurred before June 8, 2015, so you do retain the option of keeping it ' +
                        'private. However, if you do choose to make the registration public now, then after ' +
                        'June 8, 2015 you will not be able to return it to private. Are you sure that you would like ' +
                        'to continue?',
};

// TODO(sloria): Fix this external dependency on nodeApiUrl
var URLS = {
    makePublic: window.nodeApiUrl + 'permissions/public/',
    makePrivate: window.nodeApiUrl + 'permissions/private/'
};
var PUBLIC = 'public';
var PRIVATE = 'private';
var PROJECT = 'project';
var COMPONENT = 'component';


function setPermissions(permissions, nodeType) {

    var msgKey;
    // TODO(hrybacki): Remove once Retraction/Embargoes goes is merged into production
    var isRegistration = window.contextVars.node.isRegistration;

    if (permissions === PUBLIC && isRegistration) { msgKey = 'makeRegistrationPublicWarning'; }
    else if(permissions === PUBLIC && nodeType === PROJECT) { msgKey = 'makeProjectPublicWarning'; }
    else if(permissions === PUBLIC && nodeType === COMPONENT) { msgKey = 'makeComponentPublicWarning'; }
    else if(permissions === PRIVATE && nodeType === PROJECT) { msgKey = 'makeProjectPrivateWarning'; }
    else { msgKey = 'makeComponentPrivateWarning'; }

    var urlKey = permissions === PUBLIC ? 'makePublic' : 'makePrivate';
    var message = MESSAGES[msgKey];

    var confirmModal = function (message) {
        bootbox.confirm({
            title: 'Warning',
            message: message,
            callback: function(result) {
                if (result) {
                    osfHelpers.postJSON(
                        URLS[urlKey],
                        {permissions: permissions}
                    ).done(function() {
                        window.location.reload();
                    }).fail(
                        osfHelpers.handleJSONError
                    );
                }
            }
        });
    };

    if (permissions === PUBLIC) {
        $.getJSON(
            window.nodeApiUrl + 'permissions/beforepublic/',
            {},
            function(data) {
                var alerts = '';
                var addonMessages = data.prompts;
                    for(var i=0; i<addonMessages.length; i++) {
                        alerts += '<div class="alert alert-warning">' +
                                    addonMessages[i] + '</div>';
                    }
                confirmModal(alerts + message);
            }
        );
    } else {
        confirmModal(message);
    }
}

/**
 * The ProjectViewModel, scoped to the project header.
 * @param {Object} data The parsed project data returned from the project's API url.
 */
var ProjectViewModel = function(data) {
    var self = this;
    self._id = data.node.id;
    self.apiUrl = data.node.api_url;
    self.dateCreated = new osfHelpers.FormattableDate(data.node.date_created);
    self.dateModified = new osfHelpers.FormattableDate(data.node.date_modified);
    self.dateForked = new osfHelpers.FormattableDate(data.node.forked_date);
    self.parent = data.parent_node;
    self.doi = ko.observable(data.node.identifiers.doi);
    self.ark = ko.observable(data.node.identifiers.ark);
    self.idCreationInProgress = ko.observable(false);
    self.watchedCount = ko.observable(data.node.watched_count);
    self.userIsWatching = ko.observable(data.user.is_watching);
    self.dateRegistered = new osfHelpers.FormattableDate(data.node.registered_date);
    self.inDashboard = ko.observable(data.node.in_dashboard);
    self.dashboard = data.user.dashboard_id;
    self.userCanEdit = data.user.can_edit;
    self.userPermissions = data.user.permissions;
    self.description = data.node.description;
    self.title = data.node.title;
    self.category = data.node.category;
    self.isRegistration = data.node.is_registration;
    self.user = data.user;
    self.nodeIsPublic = data.node.is_public;
    self.nodeType = data.node.node_type;
    // The button text to display (e.g. "Watch" if not watching)
    self.watchButtonDisplay = ko.pureComputed(function() {
        return self.watchedCount().toString();
    });
    self.watchButtonAction = ko.pureComputed(function() {
        return self.userIsWatching() ? 'Unwatch' : 'Watch';
    });

    self.canBeOrganized = ko.pureComputed(function() {
        return !!(self.user.username && (self.nodeIsPublic || self.user.has_read_permissions));
    });

    // Add icon to title
    self.icon = '';
    var category = data.node.category_short;
    if (Object.keys(iconmap.componentIcons).indexOf(category) >=0 ){
        self.icon = iconmap.componentIcons[category];
    }
    else {
        self.icon = iconmap.projectIcons[category];
    }

    // Editable Title and Description
    if (self.userCanEdit) {
        var editableOptions = {
            type: 'text',
            pk: self._id,
            url: self.apiUrl + 'edit/',
            ajaxOptions: {
                type: 'POST',
                dataType: 'json',
                contentType: 'application/json'
            },
            params: function (params) {
                // Send JSON data
                return JSON.stringify(params);
            },
            success: function () {
                document.location.reload(true);
            },
            error: osfHelpers.handleEditableError,
            placement: 'bottom'
        };

        // TODO: Remove hardcoded selectors.
        $.fn.editable.defaults.mode = 'inline';
        $('#nodeTitleEditable').editable($.extend({}, editableOptions, {
            name: 'title',
            title: 'Edit Title',
            validate: function (value) {
                if ($.trim(value) === '') {
                    return 'Title cannot be blank.';
                }
            }
        }));
        $('#nodeDescriptionEditable').editable($.extend({}, editableOptions, {
            name: 'description',
            title: 'Edit Description',
            emptytext: 'No description',
            emptyclass: 'text-muted'
        }));
    }

    /**
     * Add project to the Project Organizer.
     */
    self.addToDashboard = function() {
        self.inDashboard(true);
        var jsonData = {
            'toNodeID': self.dashboard,
            'pointerID': self._id
        };
        osfHelpers.postJSON('/api/v1/pointer/', jsonData)
            .fail(function(data) {
                self.inDashboard(false);
                osfHelpers.handleJSONError(data);
        });
    };
    /**
     * Remove project from the Project Organizer.
     */
    self.removeFromDashboard = function() {
        self.inDashboard(false);
        var deleteUrl = '/api/v1/folder/' + self.dashboard + '/pointer/' + self._id;
        $.ajax({url: deleteUrl, type: 'DELETE'})
            .fail(function() {
                self.inDashboard(true);
                osfHelpers.growl('Error', 'The project could not be removed', 'danger');
        });
    };


    /**
     * Toggle the watch status for this project.
     */
    self.toggleWatch = function() {
        // Send POST request to node's watch API url and update the watch count
        if(self.userIsWatching()) {
            self.watchedCount(self.watchedCount() - 1);
        } else {
            self.watchedCount(self.watchedCount() + 1);
        }
        osfHelpers.postJSON(
            self.apiUrl + 'togglewatch/',
            {}
        ).done(function(data) {
            // Update watch count in DOM
            self.userIsWatching(data.watched);
            self.watchedCount(data.watchCount);
        }).fail(
            osfHelpers.handleJSONError
        );
    };

    self.makePublic = function() {
        return setPermissions(PUBLIC, self.nodeType);
    };

    self.makePrivate = function() {
        return setPermissions(PRIVATE, self.nodeType);
    };

    self.forkNode = function() {
        NodeActions.forkNode();
    };

    self.hasIdentifiers = ko.pureComputed(function() {
        return !!(self.doi() && self.ark());
    });

    self.canCreateIdentifiers = ko.pureComputed(function() {
        return !self.hasIdentifiers() &&
            self.isRegistration &&
            self.nodeIsPublic &&
            self.userPermissions.indexOf('admin') !== -1;
    });

    self.doiUrl = ko.pureComputed(function() {
        return self.doi() ? 'http://ezid.cdlib.org/id/doi:' + self.doi() : null;
    });

    self.arkUrl = ko.pureComputed(function() {
        return self.ark() ? 'http://ezid.cdlib.org/id/ark:/' + self.ark() : null;
    });

    self.askCreateIdentifiers = function() {
        var self = this;
        bootbox.confirm({
            title: 'Create identifiers',
            message: '<p class="overflow">' +
                'Are you sure you want to create a DOI and ARK for this ' +
                self.nodeType + '?',
            callback: function(confirmed) {
                if (confirmed) {
                    self.createIdentifiers();
                }
            }
        });
    };

    self.createIdentifiers = function() {
        // Only show loading indicator for slow responses
        var timeout = setTimeout(function() {
            self.idCreationInProgress(true); // show loading indicator
        }, 500);
        var url = self.apiUrl + 'identifiers/';
        return $.post(
            url
        ).done(function(resp) {
            self.doi(resp.doi);
            self.ark(resp.ark);
        }).fail(function(xhr) {
            var message = 'We could not create the identifier at this time. ' +
                'The DOI/ARK acquisition service may be down right now. ' +
                'Please try again soon and/or contact ' +
                '<a href="mailto: support@osf.io">support@osf.io</a>';
            osfHelpers.growl('Error', message, 'danger');
            Raven.captureMessage('Could not create identifiers', {url: url, status: xhr.status});
        }).always(function() {
            clearTimeout(timeout);
            self.idCreationInProgress(false); // hide loading indicator
        });
    };
};

////////////////
// Public API //
////////////////

var defaults = {
    removeCss: '.user-quickedit'
};

function NodeControl (selector, data, options) {
    var self = this;
    self.selector = selector;
    self.$element = $(self.selector);
    self.data = data;
    self.viewModel = new ProjectViewModel(self.data);
    self.options = $.extend({}, defaults, options);
    self.init();
}

NodeControl.prototype.init = function() {
    var self = this;
    osfHelpers.applyBindings(self.viewModel, this.selector);
};

module.exports = {
    _ProjectViewModel: ProjectViewModel,
    NodeControl: NodeControl
};
