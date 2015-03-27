'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers.js');
var ko = require('knockout');
var oop = require('js/oop.js');
var Raven = require('raven-js');

require('knockout.punches');
ko.punches.enableAll();


var userEmail = oop.defclass({
    constructor: function(data) {
        this.address = ko.observable();
        this.isConfirmed = ko.observable();
        this.isPrimary = ko.observable();
        if (typeof(data) !== 'undefined') {
            this.unserialize(data);
        }
    },
    serialize: function() {
        return {
            address: this.address(),
            primary: this.isPrimary(),
            confirmed: this.isConfirmed()
        };
    },
    unserialize: function(data) {
        this.address(data.address);
        this.isPrimary(data.primary || false);
        this.isConfirmed(data.confirmed || false);
    }
});


var userProfile = oop.defclass({
    constructor: function(urls) {
        this.urls = urls;

        // TODO: Pass these in instead!
        this.urls = {
            fetch: '/api/v1/profile/',
            update: '/api/v1/profile/'
        };

        this.id = ko.observable();
        this.emails = ko.observableArray();

        this.primaryEmail = ko.computed(function () {
            var emails = this.emails();
            for (var i = 0; i < this.emails().length; i++) {
                if(emails[i].isPrimary()) {
                    return emails[i];
                }
            }
            return new userEmail();
        }.bind(this));

        this.alternateEmails = ko.computed(function () {
            var emails = this.emails();
            var retval = [];
            for (var i = 0; i < this.emails().length; i++) {
                if (emails[i].isConfirmed() && !emails[i].isPrimary()) {
                    retval.push(emails[i]);
                }
            }
            return retval;
        }.bind(this));

        this.unconfirmedEmails = ko.computed(function () {
            var emails = this.emails();
            var retval = [];
            for (var i = 0; i < this.emails().length; i++) {
                if(!emails[i].isConfirmed()) {
                    retval.push(emails[i]);
                }
            }
            return retval;
        }.bind(this));

        // user inputs
        this.emailInput = ko.observable();
    },
    init: function () {
        this.fetchData(this.unserialize.bind(this));
    },
    serialize: function () {
        var emails = ko.utils.arrayMap(this.emails(), function(each) {
            return each.serialize();
        });
        return {
            id: this.id(),
            emails: emails
        };
    },
    unserialize: function (data) {
        var self = this;
        var profile = data.profile;

        this.id(profile.id);
        self.emails([]);
        ko.utils.arrayMap(profile.emails, function(each) {
            self.emails.push(new userEmail(each));
        });
    },
    fetchData: function (callback) {
        var url = '/api/v1/profile/';
        var request = $.get(url);
        request.done(callback);
        request.fail(function(xhr, status, error) {
            $osf.growl('Error', 'Could not fetch user profile.', 'danger');
            Raven.captureMessage('Error fetching user profile', {
                url: url,
                status: status,
                error: error
            });
        });
    },
    pushUpdates: function (callback) {
        var request = $osf.putJSON(this.urls.update, this.serialize());
        request.done(function(data) {
            this.unserialize(data);
            if (typeof(callback) !== 'undefined') {
                callback();
            }
        }.bind(this));
        request.fail(function(xhr, status, error) {
            $osf.growl('Error', 'User profile not updated.', 'danger');
            Raven.captureMessage('Error fetching user profile', {
                url: this.urls.update,
                status: status,
                error: error
            });
        });

        return request;

    },
    addEmail: function () {
        var email = new userEmail({address: this.emailInput()});
        this.emails.push(email);
        this.pushUpdates(function () {
            var emails = this.emails();
            for (var i=0; i<emails.length; i++) {
                if (emails[i].address() === email.address()) {
                    this.emailInput('');
                    return;
                }
            }
            $osf.growl('Error', 'Email validation failed', 'danger');
        }.bind(this));
        foo = this;
    },
    removeEmail: function (email) {
        this.emails.remove(email);
        this.pushUpdates().done(function() {
            $osf.growl('Email Removed', '<em>' + email.address()  + '<em>', 'success');
        });
    },
    makeEmailPrimary: function (email) {
        this.primaryEmail().isPrimary(false);
        email.isPrimary(true);
        this.pushUpdates();
    },
});

module.exports = {
    userProfile: userProfile
};