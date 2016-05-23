/**
* Controls the actions in the project header (make public/private, watch button,
* forking, etc.)
*/
'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
require('bootstrap-editable');
var ko = require('knockout');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');

var iconmap = require('js/iconmap');
var NodeActions = require('js/project.js');
var NodesPrivacy = require('js/nodesPrivacy').NodesPrivacy;

/**
 * The ProjectViewModel, scoped to the project header.
 * @param {Object} data The parsed project data returned from the project's API url.
 * @param {Object} options A set of configuration options for viewModel
 * @param {Object} options.categories The CATEGORY_MAP of allowed category/ display values for nodes
 */
var ProjectViewModel = function(data, options) {
    var self = this;
    self.categories = (options && options.categories) || {};
    
    self._id = data.node.id;
    self.apiUrl = data.node.api_url;
    self.dateCreated = new $osf.FormattableDate(data.node.date_created);
    self.dateModified = new $osf.FormattableDate(data.node.date_modified);
    self.dateForked = new $osf.FormattableDate(data.node.forked_date);
    self.parent = data.parent_node;
    self.doi = ko.observable(data.node.identifiers.doi);
    self.ark = ko.observable(data.node.identifiers.ark);
    self.idCreationInProgress = ko.observable(false);
    self.watchedCount = ko.observable(data.node.watched_count);
    self.userIsWatching = ko.observable(data.user.is_watching);
    self.dateRegistered = new $osf.FormattableDate(data.node.registered_date);
    self.inDashboard = ko.observable(data.node.in_dashboard);
    self.dashboard = data.user.dashboard_id;
    self.userCanEdit = data.user.can_edit;
    self.userPermissions = data.user.permissions;
    self.node = data.node;
    self.description = ko.observable(data.node.description);
    self.title = data.node.title;
    self.categoryValue = ko.observable(data.node.category_short);
    self.isRegistration = data.node.is_registration;
    self.user = data.user;
    self.nodeIsPublic = data.node.is_public;
    self.nodeType = data.node.node_type;

    self.nodeIsPendingEmbargoTermination = ko.observable(data.node.is_pending_embargo_termination);
    self.makePublicTooltip = ko.computed(function() {
        if(self.nodeIsPendingEmbargoTermination()) {
            return 'A request to make this registration public is pending';
        }
        return null;
    });

    // WATCH button is removed, functionality is still here in case of future implementation -- CU
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
    self.icon = ko.pureComputed(function() {
        var category = self.categoryValue();
        if (Object.keys(iconmap.componentIcons).indexOf(category) >=0 ){
            return iconmap.componentIcons[category];
        } else {
            return iconmap.projectIcons[category];
        }
    });

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
            error: $osf.handleEditableError,
            placement: 'bottom'
        };

        // TODO: Remove hardcoded selectors.
        $.fn.editable.defaults.mode = 'inline';
        $('#nodeTitleEditable').editable($.extend({}, editableOptions, {
            name: 'title',
            title: 'Edit Title',
            tpl: '<input type="text" maxlength="200">',
            validate: function (value) {
                if ($.trim(value) === '') {
                    return 'Title cannot be blank.';
                }
                else if(value.length > 200){
                    return 'Title cannot exceed 200 characters.';
                }
            }
        }));

        $('#nodeDescriptionEditable').editable($.extend({}, editableOptions, {
            name: 'description',
            title: 'Edit Description',
            emptytext: 'No description',
            emptyclass: 'text-muted',
            value: self.description(),
            success: function(response, newValue) {
                newValue = response.newValue; // Update display to reflect changes, eg by sanitizer
                self.description(newValue);
                return {newValue: newValue};
            }
        }));

        var categoryOptions = $.map(self.categories, function(display, value) {
            return {value: value, text: display};
        });
        $('#nodeCategoryEditable').editable($.extend({}, editableOptions, {
            type: 'select',
            name: 'category',
            title: 'Select a category',
            value: self.categoryValue(),
            source: categoryOptions,
            success: function(response, newValue) {
                newValue = response.newValue;
                self.categoryValue(newValue);
                return {newValue: newValue};
            }
        }));
    }

    /**
     * Add project to the Project Organizer.
     */
    self.addToDashboard = function() {
        $('#addDashboardFolder').tooltip('hide');
        self.inDashboard(true);
        var jsonData = {
            'toNodeID': self.dashboard,
            'pointerID': self._id
        };
        $osf.postJSON('/api/v1/pointer/', jsonData)
            .fail(function(data) {
                self.inDashboard(false);
                $osf.handleJSONError(data);
        });
    };
    /**
     * Remove project from the Project Organizer.
     */
    self.removeFromDashboard = function() {
        $('#removeDashboardFolder').tooltip('hide');
        self.inDashboard(false);
        var deleteUrl = $osf.apiV2Url('collections/' + self.dashboard + '/relationships/linked_nodes/');
        $osf.ajaxJSON('DELETE', deleteUrl, {
            'data': {'data': [{'type':'linked_nodes', 'id': self._id}]},
            'isCors': true
        }).fail(function() {
            self.inDashboard(true);
            $osf.growl('Error', 'The project could not be removed', 'danger');
        });
    };


    /**
     * Toggle the watch status for this project.
     */
    var watchUpdateInProgress = false;
    self.toggleWatch = function() {
        // When there is no watch-update in progress,
        // send POST request to node's watch API url and update the watch count
        if(!watchUpdateInProgress) {
            if (self.userIsWatching()) {
                self.watchedCount(self.watchedCount() - 1);
            } else {
                self.watchedCount(self.watchedCount() + 1);
            }
            watchUpdateInProgress = true;
            $osf.postJSON(
                self.apiUrl + 'togglewatch/',
                {}
            ).done(function (data) {
                // Update watch count in DOM
                watchUpdateInProgress = false;
                self.userIsWatching(data.watched);
                self.watchedCount(data.watchCount);
            }).fail(
                $osf.handleJSONError
            );
        }
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
                $osf.htmlEscape(self.nodeType) + '?',
            callback: function(confirmed) {
                if (confirmed) {
                    self.createIdentifiers();
                }
            },
            buttons:{
                confirm:{
                    label:'Create'
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
            $osf.growl('Error', message, 'danger');
            Raven.captureMessage('Could not create identifiers', {extra: {url: url, status: xhr.status}});
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
    self.viewModel = new ProjectViewModel(self.data, options);
    self.options = $.extend({}, defaults, options);
    self.init();
}

NodeControl.prototype.init = function() {
    var self = this;
    $osf.applyBindings(self.viewModel, this.selector);
    if (self.data.user.is_admin && !self.data.node.is_retracted) {
        new NodesPrivacy('#nodesPrivacy', self.data.node, function(nodesChanged, requestedEmbargoTermination) {
            // TODO: The goal here is to update the UI of the project dashboard to
            // reflect the new privacy state(s). Unfortunately, since the components
            // view is rendered server-side we have a relatively limited capacity to
            // update the page. Once the components list is componentized we can
            // rerender just that section of the DOM (as well as updating the
            // project-specific UI).
            // For now, this method only needs to handle requests for making embargoed
            // nodes public.
            if (requestedEmbargoTermination) {
                self.viewModel.nodeIsPendingEmbargoTermination(true);
            }
        });
    }
};

module.exports = {
    _ProjectViewModel: ProjectViewModel,
    NodeControl: NodeControl
};
