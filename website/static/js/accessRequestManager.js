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

var rdmGettext = require('js/rdmGettext');
var gt = rdmGettext.rdmGettext();
var _ = function(msgid) { return gt.gettext(msgid); };

var agh = require('agh.sprintf');

var AccessRequestModel = function(accessRequest, pageOwner, isRegistration, isParentAdmin, options) {
    var self = this;
    self.options = options;
    $.extend(self, accessRequest);

    self.permission = ko.observable(accessRequest.permission);

    self.permissionText = ko.observable(self.options.permissionMap[self.permission()]);

    self.visible = ko.observable(true);

    self.pageOwner = pageOwner;

    self.expanded = ko.observable(false);

    self.toggleExpand = function() {
        self.expanded(!self.expanded());
    };

    self.serialize = function() {
        return JSON.parse(ko.toJSON(self));
    };

    self.requestAccessPayload = function(trigger, permissions, visible) {
        return {
            'data': {
                'attributes': {
                    'trigger': trigger,
                    'permissions': permissions,
                    'visible': visible
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
        };
    };

    self.respondToAccessRequest = function(trigger, data, event) {
        $osf.trackClick('button', 'click', trigger + '-project-access');
        $osf.block();
        var requestUrl = $osf.apiV2Url('actions/requests/nodes/');
        var payload = self.requestAccessPayload(trigger, self.permission(), self.visible());
        var request = $osf.ajaxJSON(
            'POST',
            requestUrl,
            {
                'isCors': true,
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
            var errorMessage = lodashGet(xhr, 'responseJSON.message') || (agh.sprintf(_('There was a problem trying to %1$s the request from the user. %2$s'),trigger,osfLanguage.REFRESH_OR_SUPPORT));
            $osf.growl(agh.sprintf(_('Could not %1$s access request'),trigger), errorMessage);
            Raven.captureMessage(agh.sprintf(_('Could not %1$s access request'),trigger), {
                extra: {
                    url: requestUrl,
                    status: status,
                    error: error
                }
            });
        });

    };

    self.profileUrl = ko.observable(accessRequest.user.url);

    self.optionsText = function(val) {
        return self.options.permissionMap[val];
    };
};


var AccessRequestsViewModel = function(accessRequests, user, isRegistration, table) {

    var self = this;

    self.original = ko.observableArray(accessRequests);

    self.table = $(table);

    self.permissionMap = {
        read: _('Read'),
        write: _('Read + Write'),
        admin: _('Administrator')
    };

    self.permissionList = Object.keys(self.permissionMap);
    self.requestToReject = ko.observable('');

    self.accessRequests = ko.observableArray();

    self.user = ko.observable(user);

    self.options = {
        permissionMap: self.permissionMap
    };

    self.accessRequests(self.original().map(function(item) {
        return new AccessRequestModel(item, self.user(), isRegistration, false, self.options);
    }));

    self.serialize = function(accessRequest) {
        return accessRequest.serialize();
    };

    self.afterRender = function(elements, data) {
        var table;
        table = self.table[0];
        if (!!table) {
            rt.responsiveTable(table);
        }
    };

    self.collapsed = ko.observable(true);

    self.onWindowResize = function() {
        self.collapsed(self.table.children().filter('thead').is(':hidden'));
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
