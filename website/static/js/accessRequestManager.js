'use strict';

var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
require('jquery-ui');
require('knockout-sortable');
var lodashGet = require('lodash.get');
var osfLanguage = require('js/osfLanguage');

var rt = require('js/responsiveTable');
var $osf = require('./osfHelpers');
require('js/filters');



// TODO: We shouldn't need both pageOwner (the current user) and currentUserCanEdit. Separate
// out the permissions-related functions and remove currentUserCanEdit.
var AccessRequestModel = function(accessRequest, currentUserCanEdit, pageOwner, isRegistration, isParentAdmin, options) {
    var self = this;
    self.options = options;
    $.extend(self, accessRequest);

    self.permission = ko.observable(accessRequest.permission);

    self.permissionText = ko.observable(self.options.permissionMap[self.permission()]);

    self.visible = ko.observable(true);

    self.currentUserCanEdit = currentUserCanEdit;
    // User is an admin on the parent project
    self.isParentAdmin = isParentAdmin;

    self.pageOwner = pageOwner;

    self.serialize = function() {
        return JSON.parse(ko.toJSON(self));
    };

    self.canEdit = ko.computed(function() {
        return self.currentUserCanEdit && !self.isParentAdmin;
    });

    self.requestAccessPayload = function(trigger) {
        return {
            'data': {
                'attributes': {
                    'trigger': trigger
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'node-requests',
                            'id': this.id
                        }
                    }
                },
                'type': 'node-request-actions'
            }
        }
    };

    self.respondToAccessRequest = function(trigger, data, event) {
        $osf.block();
        var requestUrl = $osf.apiV2Url('actions/requests/');
        var payload = self.requestAccessPayload(trigger);
        var request = $osf.ajaxJSON(
            'POST',
            requestUrl,
            {
                'is_cors': true,
                'data': payload,
                'fields': {
                    xhrFields: {withCredentials: true}
                }
            }
        );

        request.done(function() {
            window.location.reload();
        });

        request.fail(function(xhr, status, error){
            $osf.unblock();
            var errorMessage = lodashGet(xhr, 'responseJSON.message') || ('There was a problem trying to ' + trigger + ' the request from the user. ' + osfLanguage.REFRESH_OR_SUPPORT);
            $osf.growl('Could not '+ trigger + ' access request', errorMessage);
            Raven.captureMessage('Could not ' + trigger + ' access request', {
                extra: {
                    url: requestUrl,
                    status: status,
                    error: error
                }
            });
        });

    };

    self.profileUrl = ko.observable(accessRequest.user.url);

    self.canReject = ko.computed(function(){
        return (self.id === pageOwner.id) && !isRegistration && !self.isParentAdmin;
    });

    self.optionsText = function(val) {
        return self.options.permissionMap[val];
    };
};


var AccessRequestsViewModel = function(accessRequests, user, isRegistration, table) {

    var self = this;

    self.original = ko.observableArray(accessRequests);

    self.table = $(table);

    self.permissionMap = {
        read: 'Read',
        write: 'Read + Write',
        admin: 'Administrator'
    };

    self.permissionList = Object.keys(self.permissionMap);
    self.requestToReject = ko.observable('');

    self.accessRequests = ko.observableArray();

    self.user = ko.observable(user);
    self.canEdit = ko.computed(function() {
        return ($.inArray('admin', user.permissions) > -1) && !isRegistration;
    });

    self.options = {
        permissionMap: self.permissionMap
    };

    self.init = function() {
        self.accessRequests(self.original().map(function(item) {
            return new AccessRequestModel(item, self.canEdit(), self.user(), isRegistration, false, self.options);
        }));
    };

    self.init();

    self.serialize = function(accessRequest) {
        return accessRequest.serialize();
    };

};

////////////////
// Public API //
////////////////

function AccessRequestManager(selector, accessRequests, user, isRegistration, table) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.accessRequests = accessRequests;
    self.viewModel = new AccessRequestsViewModel(accessRequests, user, isRegistration, table);

    self.init();
}

AccessRequestManager.prototype.init = function() {
    $osf.applyBindings(this.viewModel, this.$element[0]);
    this.$element.show();
};

module.exports = AccessRequestManager;
