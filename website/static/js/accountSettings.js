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
        this.unserialize(data);
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
        ko.utils.arrayMap(profile.emails, function(each) {
            self.emails.push(new userEmail(each));
        });
    },
    fetchData: function (callback) {
        var url = '/api/v1/profile/';
        var request = $.get(url);
        request.done(callback);
        request.fail(function(xhr, status, error) {
            Raven.captureMessage('Error fetching user profile', {
                url: url,
                status: status,
                error: error
            });
        });
    },
    pushUpdates: function () {
        var request = $osf.putJSON(this.urls.update, this.serialize());
        request.done(function(data) {
           console.log(data);
        });
        request.fail(function() {
            console.log('fail');
        });

        return request;

    },
    addEmail: function () {
        this.emails.push(
            new userEmail({address: this.emailInput()})
        );
        this.pushUpdates();
    },
    removeEmail: function (email) {
        this.emails.remove(email);
        this.pushUpdates();
    }
});

module.exports = {
    userProfile: userProfile
};