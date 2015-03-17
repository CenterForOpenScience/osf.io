var $ = require('jquery');
var $osf = require('js/osfHelpers');
var ko = require('knockout');
require('knockout-punches');
var md5 = require('js-md5');
var Raven = require('raven-js');

ko.punches.enableAll();


var DeactivateAccountViewModel = function (accountId) {
    var self = this;

    self.verifyId = ko.observable();
    self.accountId = accountId;
    self.verificationHash = ko.computed(function() {
        return md5(self.verifyId() ? self.verifyId() : '');
    });

    self.submit = function () {
        var url = '/api/v1/profile/';

        var request = $osf.deleteJSON(
            url,
            { verificationHash: self.verificationHash() }
        );
        request.done(function() {
            //TODO: Block the page, refresh upon dismiss.
            window.location = '/';
        });
        request.fail(function(xhr, status, error) {
            $osf.growl('Error', 'Account Deactivation Failed');
            Raven.captureMessage('Account deactivation failed', {
                url: url,
                status: status,
                error: error,
                extra: {
                    userId: self.accountId
                }
            });
        });
        return request;
    };
};


$osf.applyBindings(
    new DeactivateAccountViewModel('dj52g'),
    '#deactivateAccount'
);