/*
 * forgot password view model
 */
'use strict';

var ko = require('knockout');
require('knockout.validation');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var formViewModel = require('js/formViewModel');

var ForgotPasswordViewModel = oop.extend(formViewModel.FormViewModel, {
    constructor: function() {
        var self = this;
        self.super.constructor.call(self);
        self.username = ko.observable('').extend({
            required: true,
            email: true
        });
    },
    isValid: function() {
        var validationError = new formViewModel.ValidationError();
        if (!this.username.isValid()) {
            validationError.messages.push('Please enter a valid email address.');
            throw validationError;
        } else {
            return true;
        }
    }
});


var ForgotPassword = function(selector) {
    this.viewModel = new ForgotPasswordViewModel();
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    ForgotPassword: ForgotPassword,
    ViewModel: ForgotPasswordViewModel
};
