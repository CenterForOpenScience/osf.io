'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var ko = require('knockout');
var oop = require('js/oop');
var Raven = require('raven-js');

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
            $osf.growl('Error', 'User profile not updated.', 'danger');
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
                var email = new UserEmail();
                email.address(emailData.address);
                email.isPrimary(emailData.primary || false);
                email.isConfirmed(emailData.confirmed || false);
                return email;
            })
        );

        return profile;
    }
});


var UserProfileViewModel = oop.defclass({
    constructor: function() {
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
        var email = new UserEmail({
            address: this.emailInput()
        });
        this.profile().emails.push(email);

        this.client.update(this.profile()).done(function (profile) {
            this.profile(profile);

            var emails = profile.emails();
            for (var i=0; i<emails.length; i++) {
                if (emails[i].address() === email.address()) {
                    this.emailInput('');
                    $osf.growl('Email Added', '<em>' + email.address()  + '<em>', 'success');
                    return;
                }
            }
            $osf.growl('Error', 'Email validation failed', 'danger');
        }.bind(this));
    },
    removeEmail: function (email) {
        this.profile().emails.remove(email);
        this.client.update(this.profile()).done(function() {
            $osf.growl('Email Removed', '<em>' + email.address()  + '<em>', 'success');
        });
    },
    makeEmailPrimary: function (email) {
        this.profile().primaryEmail().isPrimary(false);
        email.isPrimary(true);
        this.client.update(this.profile()).done(function () {
            $osf.growl('Made Primary', '<em>' + email.address()  + '<em>', 'success');
        });
    }
});

module.exports = {
    UserProfileViewModel: UserProfileViewModel
};