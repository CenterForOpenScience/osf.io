'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var bootbox = require('bootbox');
var ko = require('knockout');
var oop = require('js/oop');
var Raven = require('raven-js');
var ChangeMessageMixin = require('js/changeMessage');

require('knockout.punches');
ko.punches.enableAll();


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
        update: '/api/v1/profile/'
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
                url: this.urls.fetch,
                status: status,
                error: error
            });
            ret.reject(xhr, status, error);
        }.bind(this));

        return ret.promise();
    },
    update: function (profile) {
        var ret = $.Deferred();
        var request = $osf.putJSON(
            this.urls.update,
            this.serialize(profile)
        ).done(function (data) {
            ret.resolve(this.unserialize(data, profile));
        }.bind(this)).fail(function(xhr, status, error) {
            $osf.growl('Error', 'User profile not updated. Please refresh the page and try ' +
                'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                'if the problem persists.', 'danger');
            Raven.captureMessage('Error fetching user profile', {
                url: this.urls.update,
                status: status,
                error: error
            });
                ret.reject(xhr, status, error);
        }.bind(this));

        return ret;
    },
    serialize: function (profile) {
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
        this.emailInput = ko.observable();

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
                for (var i=0; i<emails.length; i++) {
                    if (emails[i].address() === email.address()) {
                        this.emailInput('');
                        $osf.growl('<em>' + email.address()  + '<em> added to your account.','You will receive a confirmation email at <em>' + email.address()  + '<em>. Please check your email and confirm.', 'success');
                        return;
                    }
                }
                this.changeMessage('Invalid Email.', 'text-danger');
            }.bind(this));
        } else {
            this.changeMessage('Email cannot be empty.', 'text-danger');
        }
    },
    removeEmail: function (email) {
        var self = this;
        self.changeMessage('', 'text-info');
        if (self.profile().emails().indexOf(email) !== -1) {
            bootbox.confirm({
                title: 'Remove Email?',
                message: 'Are you sure that you want to remove ' + '<em><b>' + email.address() + '</b></em>' + ' from your email list?',
                callback: function (confirmed) {
                    if (confirmed) {
                        self.profile().emails.remove(email);
                        self.client.update(self.profile()).done(function () {
                            $osf.growl('Email Removed', '<em>' + email.address() + '<em>', 'success');
                        });
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
                $osf.growl('Made Primary', '<em>' + email.address() + '<em>', 'success');
            });
        } else {
            $osf.growl('Error', 'Please refresh the page and try again.', 'danger');
        }
    }
});


var DeactivateAccountViewModel = oop.defclass({
    constructor: function () {
        this.success = ko.observable(false);
    },
    urls: {
        'update': '/api/v1/profile/deactivate/'
    },
    submit: function () {
        var request = $osf.postJSON(this.urls.update, {});
        request.done(function() {
            $osf.growl('Success', 'An OSF administrator will contact you shortly to confirm your deactivation request.', 'success');
            this.success(true);
        }.bind(this));
        request.fail(function(xhr, status, error) {
            $osf.growl('Error',
                'Deactivation request failed. Please contact <a href="mailto: support@cos.io">support@cos.io</a> if the problem persists.',
                'danger'
            );
            Raven.captureMessage('Error requesting account deactivation', {
                url: this.urls.update,
                status: status,
                error: error
            });
        }.bind(this));
        return request;
    }
});


var ExportAccountViewModel = oop.defclass({
    constructor: function () {
        this.success = ko.observable(false);
    },
    urls: {
        'update': '/api/v1/profile/export/'
    },
    submit: function () {
        var request = $osf.postJSON(this.urls.update, {});
        request.done(function() {
            $osf.growl('Success', 'An OSF administrator will contact you shortly to confirm your export request.', 'success');
            this.success(true);
        }.bind(this));
        request.fail(function(xhr, status, error) {
            $osf.growl('Error',
                'Export request failed. Please contact <a href="mailto: support@cos.io">support@cos.io</a> if the problem persists.',
                'danger'
            );
            Raven.captureMessage('Error requesting account export', {
                url: this.urls.update,
                status: status,
                error: error
            });
        }.bind(this));
        return request;
    }
});

module.exports = {
    UserProfileViewModel: UserProfileViewModel,
    DeactivateAccountViewModel: DeactivateAccountViewModel,
    ExportAccountViewModel: ExportAccountViewModel
};
