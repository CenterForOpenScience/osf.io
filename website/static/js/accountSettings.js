'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var bootbox = require('bootbox');
var ko = require('knockout');
var oop = require('js/oop');
var Raven = require('raven-js');
var ChangeMessageMixin = require('js/changeMessage');


var UserEmail = oop.defclass({
    constructor: function(params) {
        params = params || {};
        this.address = ko.observable(params.address);
        this.isConfirmed = ko.observable(params.isConfirmed || false);
        this.isPrimary = ko.observable(params.isPrimary || false);
    }
});


var UserProfile = oop.defclass({
    constructor: function () {

        this.id = ko.observable();
        this.emails = ko.observableArray();
        this.defaultRegion = ko.observable();
        this.availableRegions = ko.observableArray();

        this.primaryEmail = ko.pureComputed(function () {
            var emails = this.emails();
            for (var i = 0; i < this.emails().length; i++) {
                if(emails[i].isPrimary()) {
                    return emails[i];
                }
            }
            return new UserEmail();
        }.bind(this));

        this.alternateEmails = ko.pureComputed(function () {
            var emails = this.emails();
            var retval = [];
            for (var i = 0; i < this.emails().length; i++) {
                if (emails[i].isConfirmed() && !emails[i].isPrimary()) {
                    retval.push(emails[i]);
                }
            }
            return retval;
        }.bind(this));

        this.unconfirmedEmails = ko.pureComputed(function () {
            var emails = this.emails();
            var retval = [];
            for (var i = 0; i < this.emails().length; i++) {
                if(!emails[i].isConfirmed()) {
                    retval.push(emails[i]);
                }
            }
            return retval;
        }.bind(this));

    }
});


var UserProfileClient = oop.defclass({
    constructor: function () {},
    urls: {
        fetch: '/api/v1/profile/',
        update: '/api/v1/profile/',
        resend: '/api/v1/resend/'
    },
    fetch: function () {
        var ret = $.Deferred();

        var request = $.get(this.urls.fetch);
        request.done(function(data) {
            ret.resolve(this.unserialize(data));
        }.bind(this));
        request.fail(function(xhr, status, error) {
            $osf.growl('Error', 'Could not fetch user profile.', 'danger');
            Raven.captureMessage('Error fetching user profile', {
                extra: {
                    url: this.urls.fetch,
                    status: status,
                    error: error
                }
            });
            ret.reject(xhr, status, error);
        }.bind(this));

        return ret.promise();
    },
    update: function (profile, email) {
        var url = this.urls.update;
        if(email) {
            url = this.urls.resend;
        }
        var ret = $.Deferred();
        var request = $osf.putJSON(
            url,
            this.serialize(profile, email)
        ).done(function (data) {
            ret.resolve(this.unserialize(data, profile));
        }.bind(this)).fail(function(xhr, status, error) {
            if (xhr.status === 400) {
                $osf.growl('Error', xhr.responseJSON.message_long);

            } else {
                $osf.growl('Error', 'User profile not updated. Please refresh the page and try ' +
                'again or contact ' + $osf.osfSupportLink() + ' if the problem persists.', 'danger');
            }

            Raven.captureMessage('Error fetching user profile', {
                extra: {
                    url: this.urls.update,
                    status: status,
                    error: error
                }
            });
            ret.reject(xhr, status, error);
        }.bind(this));

        return ret;
    },
    serialize: function (profile, email) {
        if(email){
            return {
                id: profile.id(),
                email: {
                    address: email.address(),
                    primary: email.isPrimary(),
                    confirmed: email.isConfirmed()
                }
            };
        }
        return {
            id: profile.id(),
            emails: ko.utils.arrayMap(profile.emails(), function(email) {
                return {
                    address: email.address(),
                    primary: email.isPrimary(),
                    confirmed: email.isConfirmed()
                };
            })

        };
    },
    unserialize: function (data, profile) {
        if (typeof(profile) === 'undefined') {
            profile = new UserProfile();
        }

        profile.id(data.profile.id);
        profile.defaultRegion(data.profile.default_region);
        profile.availableRegions(data.profile.available_regions);
        profile.emails(
            ko.utils.arrayMap(data.profile.emails, function (emailData){
                var email = new UserEmail({
                    address: emailData.address,
                    isPrimary: emailData.primary,
                    isConfirmed: emailData.confirmed
                });
                return email;
            })
        );

        return profile;
    }
});


var UserProfileViewModel = oop.extend(ChangeMessageMixin, {
    constructor: function() {
        this.super.constructor.call(this);
        this.client = new UserProfileClient();
        this.profile = ko.observable(new UserProfile());
        this.emailInput = ko.observable('');

    },
    init: function () {
        this.client.fetch().done(
            function(profile) { this.profile(profile); }.bind(this)
        );
    },
    addEmail: function () {
        this.changeMessage('', 'text-info');
        var newEmail = this.emailInput().toLowerCase().trim();
        if(newEmail){

            var email = new UserEmail({
                address: newEmail
            });

            // ensure email isn't already in the list
            for (var i=0; i<this.profile().emails().length; i++) {
                if (this.profile().emails()[i].address() === email.address()) {
                    this.changeMessage('Duplicate Email', 'text-warning');
                    this.emailInput('');
                    return;
                }
            }

            this.profile().emails.push(email);

            this.client.update(this.profile()).done(function (profile) {
                this.profile(profile);
                var emails = profile.emails();
                var emailAdded = false;
                for (var i=0; i<emails.length; i++) {
                    if (emails[i].address() === email.address()) {
                        emailAdded = true;
                        this.emailInput('');
                    }
                }
                if (emailAdded === true) {
                    var safeAddr = $osf.htmlEscape(email.address());
                    bootbox.alert({
                                title: 'Confirmation email sent',
                                message: '<em>' + safeAddr + '</em>' + ' was added to your account.' +
                                ' You will receive a confirmation email at ' + '<em>' + safeAddr + '</em>.' +
                                ' Please click the link in your email to confirm this action. You will be required to enter your password.',
                                buttons: {
                                    ok: {
                                        label: 'Close',
                                        className: 'btn-default'
                                    }
                                }
                            });
                }
            }.bind(this)).fail(function(){
                this.profile().emails.remove(email);
            }.bind(this));
        } else {
            this.changeMessage('Email cannot be empty.', 'text-danger');
        }
    },
    resendConfirmation: function(email){
        var self = this;
        self.changeMessage('', 'text-info');
        var safeAddr = $osf.htmlEscape(email.address());
        bootbox.confirm({
            title: 'Resend Email Confirmation?',
            message: 'Are you sure that you want to resend email confirmation to ' + '<em>' + safeAddr + '</em>?',
            callback: function (confirmed) {
                if (confirmed) {
                    self.client.update(self.profile(), email).done(function () {
                        $osf.growl(
                            'Email confirmation resent to <em>' + safeAddr + '</em>',
                            'You will receive a new confirmation email at <em>' + safeAddr  + '</em>.' +
                            ' Please log out of this account and check your email to confirm this action.',
                            'success');
                    });
                }
            },
            buttons:{
                confirm:{
                    label:'Resend'
                }
            }
        });
    },
    removeEmail: function (email) {
        var self = this;
        self.changeMessage('', 'text-info');
        if (self.profile().emails().indexOf(email) !== -1) {
            var addrText = $osf.htmlEscape(email.address());
            bootbox.confirm({
                title: 'Remove Email?',
                message: 'Are you sure that you want to remove ' + '<em>' + addrText + '</em>' + ' from your email list?',
                callback: function (confirmed) {
                    if (confirmed) {
                        self.profile().emails.remove(email);
                        self.client.update(self.profile()).done(function () {
                            $osf.growl('Email Removed', '<em>' + addrText + '</em>', 'success');
                        });
                    }
                },
                buttons:{
                    confirm:{
                        label:'Remove',
                        className:'btn-danger'
                    }
                }
            });
        } else {
            $osf.growl('Error', 'Please refresh the page and try again.', 'danger');
        }
    },
    makeEmailPrimary: function (email) {
        this.changeMessage('', 'text-info');
        if (this.profile().emails().indexOf(email) !== -1) {
            this.profile().primaryEmail().isPrimary(false);
            email.isPrimary(true);
            this.client.update(this.profile()).done(function () {
                var addrText = $osf.htmlEscape(email.address());
                $osf.growl('Made Primary', '<em>' + addrText + '<em>', 'success');
            });
        } else {
            $osf.growl('Error', 'Please refresh the page and try again.', 'danger');
        }
    }
});

var ExternalIdentityViewModel = oop.defclass({
    constructor: function () {},
    urls: {
        'delete': '/api/v1/profile/logins/'
    },
    _removeIdentity: function(identity) {
        var request = $osf.ajaxJSON('PATCH', this.urls.delete, {'data': {'identity': identity}});
        request.done(function() {
            $osf.growl('Success', 'You have revoked this connected identity.', 'success');
            window.location.reload();
        }.bind(this));
        request.fail(function(xhr, status, error) {
            $osf.growl('Error',
                'Revocation request failed. Please contact ' + $osf.osfSupportLink() + ' if the problem persists.',
                'danger'
            );
            Raven.captureMessage('Error revoking connected identity', {
                extra: {
                    url: this.urls.update,
                    status: status,
                    error: error
                }
            });
        }.bind(this));
        return request;
    },
    removeIdentity: function (identity) {
        var self = this;
        bootbox.confirm({
            title: 'Remove authorization?',
            message: 'Are you sure you want to remove this authorization?',
            callback: function(confirmed) {
                if (confirmed) {
                    return self._removeIdentity(identity);
                }
            },
            buttons:{
                confirm:{
                    label:'Remove',
                    className:'btn-danger'
                }
            }
        });
    }
});

var UpdateDefaultStorageLocation = oop.defclass({
    constructor: function() {
        this.client = new UserProfileClient();
        this.profile = ko.observable(new UserProfile());
        this.locationSelected = ko.observable({'name': ''});

        this.locationSelectedName = ko.computed(function () {
            return this.locationSelected().name;
        }, this);


        this.client.fetch().done(
            function(profile) {
                this.profile(profile);
                this.locationSelected(this.profile().defaultRegion());
            }.bind(this)
        );


    },
    urls: {
        'update': '/api/v1/profile/region/'
    },
    updateDefaultStorageLocation: function() {
        var request = $osf.ajaxJSON('PUT', this.urls.update, {'data': {'region_id': this.locationSelected()._id}});
        request.done(function() {
            $osf.growl('Success', 'You have successfully changed your default storage location to <b>' + this.locationSelected().name + '</b>.', 'success');
        }.bind(this));
        request.fail(function(xhr, status, error) {
            $osf.growl('Error',
                'Your attempt to change your default storage location has failed. Please contact ' + $osf.osfSupportLink() + ' if the problem persists.',
                'danger'
            );
        }.bind(this));
        return request;
    },
    setLocation: function(location) {
        this.locationSelected(location);

    }
});

var DeactivateAccountViewModel = oop.defclass({
    constructor: function () {
        this.requestPending = ko.observable(window.contextVars.requestedDeactivation);
    },
    urls: {
        'update': '/api/v1/profile/deactivate/',
        'cancelDeactivate': '/api/v1/profile/cancel_request_deactivation/'
    },
    _requestDeactivation: function() {
        var request = $osf.postJSON(this.urls.update, {});
        request.done(function() {
            $osf.growl('Success', 'An OSF administrator will contact you shortly to confirm your deactivation request.', 'success');
            this.requestPending(true);
        }.bind(this));
        request.fail(function(xhr, status, error) {
            if (xhr.responseJSON.error_type === 'throttle_error') {
                $osf.growl('Error', xhr.responseJSON.message_long, 'danger');
            } else {
                $osf.growl('Error',
                    'Deactivation request failed. Please contact ' + $osf.osfSupportLink() + ' if the problem persists.',
                    'danger'
                );
            }
            Raven.captureMessage('Error requesting account deactivation', {
                extra: {
                    url: this.urls.update,
                    status: status,
                    error: error
                }
            });
        }.bind(this));
        return request;
    },
    _cancelRequestDeactivation: function() {
        var request = $osf.postJSON(this.urls.cancelDeactivate, {});
        request.done(function() {
            $osf.growl('Success', 'An OSF account is no longer up for review.', 'success');
            this.requestPending(false);
        }.bind(this));
        request.fail(function(xhr, status, error) {
            if (xhr.responseJSON.error_type === 'throttle_error') {
                $osf.growl('Error', xhr.responseJSON.message_long, 'danger');
            } else {
                $osf.growl('Error',
                    'Deactivation request failed. Please contact <a href="mailto: support@osf.io">support@osf.io</a> if the problem persists.',
                    'danger'
                );
            }
            Raven.captureMessage('Error requesting account deactivation', {
                extra: {
                    url: this.urls.rescind_deactivate,
                    status: status,
                    error: error
                }
            });
        }.bind(this));
        return request;
    },
    submit: function () {
        var self = this;
        bootbox.confirm({
            title: 'Request account deactivation?',
            message: 'Are you sure you want to request account deactivation? An OSF administrator will review your request. If accepted, you ' +
                     'will <strong>NOT</strong> be able to reactivate your account.',
            callback: function(confirmed) {
                if (confirmed) {
                    return self._requestDeactivation();
                }
            },
            buttons:{
                confirm:{
                    label:'Request',
                    className:'btn-danger'
                }
            }
        });
    },
    cancel: function () {
        var self = this;
        bootbox.confirm({
            title: 'Cancel deactivation request?',
            message: 'Are you sure you want to rescind your account deactivation request? This will preserve your account status.',
            callback: function (confirmed) {
                if (confirmed) {
                    return self._cancelRequestDeactivation();
                }
            },
            buttons: {
                confirm: {
                    label: 'Cancel Deactivation Request',
                    className: 'btn-success'
                }
            }
        });
    }
});

var ExportAccountViewModel = oop.defclass({
    constructor: function () {
        this.success = ko.observable(false);
    },
    urls: {
        'update': '/api/v1/profile/export/'
    },
    _requestExport: function() {
        var request = $osf.postJSON(this.urls.update, {});
        request.done(function() {
            $osf.growl('Success', 'An OSF administrator will contact you shortly to confirm your export request.', 'success');
            this.success(true);
        }.bind(this));
        request.fail(function(xhr, status, error) {
            if (xhr.responseJSON.error_type === 'throttle_error') {
                $osf.growl('Error', xhr.responseJSON.message_long, 'danger');
            } else {
                $osf.growl('Error',
                    'Export request failed. Please contact ' + $osf.osfSupportLink() + ' if the problem persists.',
                    'danger'
                );
            }
            Raven.captureMessage('Error requesting account export', {
                extra: {
                    url: this.urls.update,
                    status: status,
                    error: error
                }
            });
        }.bind(this));
        return request;
    },
    submit: function () {
        var self = this;
        bootbox.confirm({
            title: 'Request account export?',
            message: 'Are you sure you want to request account export?',
            callback: function(confirmed) {
                if (confirmed) {
                    return self._requestExport();
                }
            },
            buttons:{
                confirm:{
                    label:'Request'
                }
            }
        });
    }
});

module.exports = {
    UserProfileViewModel: UserProfileViewModel,
    DeactivateAccountViewModel: DeactivateAccountViewModel,
    ExportAccountViewModel: ExportAccountViewModel,
    ExternalIdentityViewModel: ExternalIdentityViewModel,
    UpdateDefaultStorageLocation: UpdateDefaultStorageLocation
};
