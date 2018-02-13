'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var bootbox = require('bootbox');
var ko = require('knockout');
var oop = require('js/oop');
var Raven = require('raven-js');
var ChangeMessageMixin = require('js/changeMessage');


var RequestAccessViewModel = oop.defclass({
    init: function() {
        $('#supportMessage').html('If this should not have occured, please contact ' + $osf.osfSupportLink() + '.')
    },
    constructor: function () {
        var self = this;
        self.AccessRequestSuccess = ko.observable(false);
        self.requestAccessButton = ko.observable('Request access');
    },
    urls: {
        'update': window.contextVars.apiV2Prefix + 'nodes/' + window.contextVars.nodeId + '/requests/'
    },
    requestProjectAccess: function() {
        var accessRequestUrl =  window.contextVars.apiV2Prefix + 'nodes/' + window.contextVars.nodeId + '/requests/';
        console.log('gonna post to '+ accessRequestUrl);
        var request = $osf.postJSON(accessRequestUrl, {
            'data': {
                'attributes': {
                    'comment': 'ASDFG',
                    'request_type': 'access'
                },
                'type': 'node-requests'
            }
        });
        var request = $.get('');
        request.done(function() {
            this.AccessRequestSuccess(true);
            this.requestAccessButton('Access requested');
            console.log('Access request successful!');
        }.bind(this));
        request.fail(function(xhr, status, error) {
            $osf.growl('Error',
                'Access request failed. Please contact ' + $osf.osfSupportLink() + ' if the problem persists.',
                'danger'
            );
            Raven.captureMessage('Error requesting project access', {
                extra: {
                    url: this.urls.update,
                    status: status,
                    error: error
                }
            });
        }.bind(this));
        return request;
    }
});

module.exports = {
    RequestAccessViewModel: RequestAccessViewModel
};
