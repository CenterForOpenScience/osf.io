/**
* Controls the actions in the project header (make public/private, forking, etc.)
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

var RequestAccess = require('js/requestAccess.js');

/**
 * The ProjectViewModel, scoped to the project header.
 * @param {Object} data The parsed project data returned from the project's API url.
 * @param {Object} options A set of configuration options for viewModel
 * @param {Object} options.categories The NODE_CATEGORY_MAP of allowed category/ display values for nodes
 */
var ProjectViewModel = function(data, options) {
    var self = this;

    self._id = data.node.id;
    self.apiUrl = data.node.api_url;
    self.dateCreated = new $osf.FormattableDate(data.node.date_created);
    self.dateModified = new $osf.FormattableDate(data.node.date_modified);
    self.dateForked = new $osf.FormattableDate(data.node.forked_date);
    self.parent = data.parent_node;
    self.doi = ko.observable(data.node.identifiers.doi);
    self.ark = ko.observable(data.node.identifiers.ark);
    self.idCreationInProgress = ko.observable(false);
    self.dateRegistered = new $osf.FormattableDate(data.node.registered_date);
    self.dateRetracted = new $osf.FormattableDate(data.node.date_retracted);
    self.inDashboard = ko.observable(data.node.in_dashboard);
    self.dashboard = data.user.dashboard_id;
    self.userCanEdit = data.user.can_edit;
    self.userPermissions = data.user.permissions;
    self.node = data.node;
    self.description = ko.observable(data.node.description ? data.node.description : '');
    self.title = data.node.title;
    self.categoryValue = ko.observable(data.node.category_short);
    self.isRegistration = data.node.is_registration;
    self.user = data.user;
    self.nodeIsPublic = data.node.is_public;
    self.nodeType = data.node.node_type;
    self.currentUserRequestState = options.currentUserRequestState;

    self.requestAccess = new RequestAccess(options.currentUserRequestState, self._id, self.user);
    self.nodeIsPendingEmbargoTermination = ko.observable(data.node.is_pending_embargo_termination);
    self.makePublicTooltip = ko.computed(function() {
        if(self.nodeIsPendingEmbargoTermination()) {
            return 'A request to make this registration public is pending';
        }
        return null;
    });

    self.canBeOrganized = ko.pureComputed(function() {
        return !!(self.user.username && (self.nodeIsPublic || self.user.has_read_permissions));
    });

    // Add icon to title
    self.icon = ko.pureComputed(function() {
        var category = self.categoryValue();
        return iconmap.projectComponentIcons[category];
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

        var project_or_component_label = self.categoryValue() === 'project' ? 'project' : 'component';
        $('#nodeDescriptionEditable').editable($.extend({}, editableOptions, {
            name: 'description',
            title: 'Edit Description',
            emptytext: 'Add a brief description to your ' + project_or_component_label,
            emptyclass: 'text-muted',
            value: $osf.decodeText(self.description()),
            success: function(response, newValue) {
                newValue = $osf.decodeText(response.newValue); // Update display to reflect changes, eg by sanitizer
                self.description(newValue);
                return {newValue: newValue};
            }
        }));

        var categories = (options && options.categories) || {};
        var categoryOptions = $.map(categories, function(item) {
            return {value: item.value, text: item.display_name};
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
    } else {
      $('#nodeDescriptionEditable').html($osf.linkifyText(self.description()));
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

    self.forkNode = function() {
        NodeActions.forkNode();
    };

    self.hasDoi = ko.pureComputed(function() {
        return !!(self.doi());
    });

    self.hasArk = ko.pureComputed(function() {
        return !!(self.ark());
    });

    self.identifier = ko.pureComputed(function(){
        return self.hasArk() && self.hasDoi()? 'Identifiers' : 'Identifier';
    });

    self.canCreateIdentifiers = ko.pureComputed(function() {
        return !self.hasDoi() &&
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
            title: 'Create DOI',
            message: '<p class="overflow">' +
                'Are you sure you want to create a DOI for this ' +
                $osf.htmlEscape(self.nodeType) + '? A DOI' +
                ' is persistent and will always resolve to this page.',
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
                'The DOI acquisition service may be down right now. ' +
                'Please try again soon and/or contact ' + $osf.osfSupportLink();
            $osf.growl('Error', message, 'danger');
            Raven.captureMessage('Could not create doi', {extra: {url: url, status: xhr.status}});
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
