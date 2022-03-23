'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var bootbox = require('bootbox');
var ko = require('knockout');
var oop = require('js/oop');
var Raven = require('raven-js');
var ChangeMessageMixin = require('js/changeMessage');

var _ = require('js/rdmGettext')._;
var sprintf = require('agh.sprintf').sprintf;

var UserEmail = oop.defclass({
    constructor: function(params) {
        params = params || {};
        this.address = ko.observable(params.address);
        this.isConfirmed = ko.observable(params.isConfirmed || false);
        this.isPrimary = ko.observable(params.isPrimary || false);
        this.allowActive = ko.observable(params.allowActive || false);
    }
});


var UserProfile = oop.defclass({
    constructor: function () {

        this.id = ko.observable();
        this.emails = ko.observableArray();
        this.defaultRegion = ko.observable();
        this.availableRegions = ko.observableArray();
        this.inactiveProfile = ko.observableArray();

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
            $osf.growl('Error', _('Could not fetch user profile.'), 'danger');
            Raven.captureMessage(_('Error fetching user profile'), {
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
                $osf.growl('Error', sprintf(_('User profile not updated. Please refresh the page and try again or contact %1$s if the problem persists.'),$osf.osfSupportLink()), 'danger');
            }

            Raven.captureMessage(_('Error fetching user profile'), {
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
                    confirmed: email.isConfirmed(),
                    allow_active: email.allowActive()
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
                    isConfirmed: emailData.confirmed,
                    allowActive: emailData.allow_active
                });
                return email;
            })
        );
        profile.inactiveProfile(data.profile.inactive_profile);

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
    addEmail: function (new_email, allow_active) {
        this.changeMessage('', 'text-info');
        var newEmail = this.emailInput().toLowerCase().trim();
        if(newEmail){

            var email = new UserEmail({
                address: newEmail,
                allowActive: newEmail === new_email ? allow_active : false
            });

            // ensure email isn't already in the list
            for (var i=0; i<this.profile().emails().length; i++) {
                if (this.profile().emails()[i].address() === email.address()) {
                    this.changeMessage(_('Duplicate Email'), 'text-warning');
                    this.emailInput('');
                    return;
                }
            }

            this.profile().emails.push(email);

            this.client.update(this.profile()).done(function (profile) {
                this.profile(profile);
                this.inactive_profile = profile.inactiveProfile();
                var emails = profile.emails();
                var emailAdded = false;
                var activationConfirm = false;
                for (var i=0; i<emails.length; i++) {
                    if (this.inactive_profile && this.inactive_profile.email === email.address()) {
                        activationConfirm = true;
                        this.emailInput(this.inactive_profile.email);
                        break;
                    }
                    if (emails[i].address() === email.address()) {
                        emailAdded = true;
                        this.emailInput('');
                    }
                }
                if (activationConfirm === true) {
                    bootbox.confirm({
                        title: _('Do you want to active account?') + '\n',
                        message: sprintf(_('Fullname: <em>%1$s</em></br>Email: <em>%2$s</em></br>'), this.inactive_profile.fullname, this.inactive_profile.email),
                        callback: function(confirmed) {
                            if (confirmed) {
                                this.addEmail(this.inactive_profile.email, true);
                            }
                        }.bind(this),
                        buttons:{
                            cancel:{
                                label:_('Cancel')
                            },
                            confirm:{
                                label:_('Active'),
                                className:'btn-success'
                            }
                        }
                    });
                }
                if (emailAdded === true) {
                    var safeAddr = $osf.htmlEscape(email.address());
                    bootbox.alert({
                                title: _('Confirmation email sent'),
                                message: sprintf(_('<em>%1$s</em> was added to your account.'),safeAddr) +
                                sprintf(_(' You will receive a confirmation email at <em>%1$s</em>.'),safeAddr) +
                                _(' Please click the link in your email to confirm this action. You will be required to enter your password.'),
                                buttons: {
                                    ok: {
                                        label: _('Close'),
                                        className: 'btn-default'
                                    }
                                }
                            });
                }
            }.bind(this)).fail(function(){
                this.profile().emails.remove(email);
            }.bind(this));
        } else {
            this.changeMessage(_('Email cannot be empty.'), 'text-danger');
        }
    },
    resendConfirmation: function(email){
        var self = this;
        self.changeMessage('', 'text-info');
        var safeAddr = $osf.htmlEscape(email.address());
        bootbox.confirm({
            title: _('Resend Email Confirmation?'),
            message: sprintf(_('Are you sure that you want to resend email confirmation to <em>%1$s</em>?'),safeAddr),
            callback: function (confirmed) {
                if (confirmed) {
                    self.client.update(self.profile(), email).done(function () {
                        $osf.growl(
                            sprintf(_('Email confirmation resent to <em>%1$s</em>'),safeAddr),
                            sprintf(_('You will receive a new confirmation email at <em>%1$s</em>.'),safeAddr) +
                            _(' Please log out of this account and check your email to confirm this action.'),
                            'success');
                    });
                }
            },
            buttons:{
                confirm:{
                    label:_('Resend')
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
                title: _('Remove Email?'),
                message: sprintf(_('Are you sure that you want to remove <em>%1$s</em> from your email list?'),addrText),
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
                        label:_('Remove'),
                        className:'btn-danger'
                    },
                    cancel:{
                        label:_('Cancel')
                    }
                }
            });
        } else {
            $osf.growl('Error', _('Please refresh the page and try again.'), 'danger');
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
            $osf.growl('Error', _('Please refresh the page and try again.'), 'danger');
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
            $osf.growl('Success', _('You have revoked this connected identity.'), 'success');
            window.location.reload();
        }.bind(this));
        request.fail(function(xhr, status, error) {
            $osf.growl('Error',
                sprintf(_('Revocation request failed. Please contact %1$s if the problem persists.'),$osf.osfSupportLink()),
                'danger'
            );
            Raven.captureMessage(_('Error revoking connected identity'), {
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
            title: _('Remove authorization?'),
            message: _('Are you sure you want to remove this authorization?'),
            callback: function(confirmed) {
                if (confirmed) {
                    return self._removeIdentity(identity);
                }
            },
            buttons:{
                confirm:{
                    label:_('Remove'),
                    className:'btn-danger'
                },
                cancel:{
                    label:_('Cancel')
                }
            }
        });
    }
});

var UpdateDefaultStorageLocation = oop.defclass({
    constructor: function() {
        var self = this;
        this.client = new UserProfileClient();
        this.profile = ko.observable(new UserProfile());
        this.locationSelected = ko.observable();
        this.locations = ko.observableArray([]);

        this.client.fetch().done(
            function(profile) {
                this.profile(profile);
                // Ensure defaultRegion is at top of region list
                this.profile().availableRegions.remove(function (item) { return item._id === self.profile().defaultRegion()._id; });
                this.profile().availableRegions.unshift(this.profile().defaultRegion());
                this.locations(this.profile().availableRegions());
                this.locationSelected(this.profile().defaultRegion);
            }.bind(this)
        );
    },
    urls: {
        'update': '/api/v1/profile/region/'
    },
    updateDefaultStorageLocation: function() {
        var request = $osf.ajaxJSON('PUT', this.urls.update, {'data': {'region_id': this.locationSelected()._id}});
        request.done(function() {
            $osf.growl('Success', sprintf(_('You have successfully changed your default storage location to <b>%1$s</b>.'),this.locationSelected().name), 'success');
        }.bind(this));
        request.fail(function(xhr, status, error) {
            $osf.growl('Error',
                sprintf(_('Your attempt to change your default storage location has failed. Please contact %1$s if the problem persists.'),$osf.osfSupportLink()),
                'danger'
            );
            Raven.captureMessage(_('Error updating default storage location '), {
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
            $osf.growl('Success', _('An GakuNin RDM administrator will contact you shortly to confirm your deactivation request.'), 'success');
            this.requestPending(true);
        }.bind(this));
        request.fail(function(xhr, status, error) {
            if (xhr.responseJSON.error_type === 'throttle_error') {
                $osf.growl('Error', xhr.responseJSON.message_long, 'danger');
            } else {
                $osf.growl('Error',
                    sprintf(_('Deactivation request failed. Please contact %1$s if the problem persists.'),$osf.osfSupportLink()),
                    'danger'
                );
            }
            Raven.captureMessage(_('Error requesting account deactivation'), {
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
            $osf.growl('Success', _('An GakuNin RDM account is no longer up for review.'), 'success');
            this.requestPending(false);
        }.bind(this));
        request.fail(function(xhr, status, error) {
            if (xhr.responseJSON.error_type === 'throttle_error') {
                $osf.growl('Error', xhr.responseJSON.message_long, 'danger');
            } else {
                $osf.growl('Error',
                    _('Deactivation request failed. Please contact <a href="mailto: rdm_support@nii.ac.jp">rdm_support@nii.ac.jp</a> if the problem persists.'),
                    'danger'
                );
            }
            Raven.captureMessage(_('Error requesting account deactivation'), {
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
            title: _('Request account deactivation?'),
            message: _('Are you sure you want to request account deactivation? A GakuNinRDM administrator will review your request. If accepted, you ') +
                     _('will <strong>NOT</strong> be able to reactivate your account.'),
            callback: function(confirmed) {
                if (confirmed) {
                    return self._requestDeactivation();
                }
            },
            buttons:{
                confirm:{
                    label:_('Request'),
                    className:'btn-danger'
                },
                cancel:{
                    label:_('Cancel')
                }
            }
        });
    },
    cancel: function () {
        var self = this;
        bootbox.confirm({
            title: _('Cancel deactivation request?'),
            message: _('Are you sure you want to rescind your account deactivation request? This will preserve your account status.'),
            callback: function (confirmed) {
                if (confirmed) {
                    return self._cancelRequestDeactivation();
                }
            },
            buttons: {
                confirm: {
                    label: _('Cancel Deactivation Request'),
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
            $osf.growl('Success', _('An GakuNin RDM administrator will contact you shortly to confirm your export request.'), 'success');
            this.success(true);
        }.bind(this));
        request.fail(function(xhr, status, error) {
            if (xhr.responseJSON.error_type === 'throttle_error') {
                $osf.growl('Error', xhr.responseJSON.message_long, 'danger');
            } else {
                $osf.growl('Error',
                    sprintf(_('Export request failed. Please contact %1$s if the problem persists.'),$osf.osfSupportLink()),
                    'danger'
                );
            }
            Raven.captureMessage(_('Error requesting account export'), {
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
            title: _('Request account export?'),
            message: _('Are you sure you want to request account export?'),
            callback: function(confirmed) {
                if (confirmed) {
                    return self._requestExport();
                }
            },
            buttons:{
                confirm:{
                    label:_('Request')
                },
                cancel:{
                    label:_('Cancel')
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
