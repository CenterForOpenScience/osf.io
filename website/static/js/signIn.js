/**
 * Sign in view model
 */
'use strict';

var ko = require('knockout');
require('knockout-validation');
var $ = require('jquery');

var $osf = require('osfHelpers');

var ViewModel = function() {

    var self = this;

    self.username = ko.observable('').extend({
        required: true,
        email: true
    });
    self.password = ko.observable('').extend({
        required: true,
        minLength: 6,  // based off signUp.js -- is this documented?
        maxLength: 35  // based off of signUp.js -- is this documented?
    });

    self.isValid = ko.computed(function() {
        return self.username.isValid() && self.password.isValid();
    });

    self.submit = function() {
        // Show errors if invalid
        if (!self.isValid()) {
            var errors = ko.validation.group(self);
            errors.showAllMessages();
            return false;
        } else {
            return true;  // Allow form to submit normally
        }
    }
};


var SignIn = function(selector, applyBindings) {
    this.viewModel = new ViewModel();
    if (applyBindings == true) {
        $osf.applyBindings(this.viewModel, selector);
    }
};

module.exports = SignIn;
