/**
 * On page load, focuses on justification input and
 * maintains knockout ViewModel
**/
'use strict';

var ko = require('knockout');
require('knockout-validation');
require('knockout-punches');
var $ = require('jquery');

var $osf = require('osfHelpers');

ko.punches.enableAll();

var RegistrationRetractionViewModel = function(submitUrl) {

    var self = this;

    // Custom Validation
    ko.validation.rules['mustEqual'] = {
        validator: function (val, otherVal) {
            return val === otherVal;
        },
        message: "The field does not match the required input."
    };
    ko.validation.registerExtenders();

    self.registrationTitle = ko.observable(contextVars.node.title);
    self.justification = ko.observable().extend({
        required: true,
        minLength: 10
    });
    self.confirmationText = ko.observable().extend({
        required: true,
        mustEqual: self.registrationTitle
    });

    self.isValid = ko.computed(function() {
        return self.justification.isValid() && self.confirmationText.isValid();
    });

    self.submit = function() {
        // Show errors if invalid
        if (!self.isValid()) {
            var errors = ko.validation.group(self);
            errors.showAllMessages();

            return false;
        } else {
            // Else Submit
            $osf.postJSON(
                submitUrl,
                ko.toJS(self)
            ).done(function (response) {
                    $(location).attr("href", response.redirectUrl);
                }
            ).fail(
                console.log('Unsuccessful submission')
            );
        }
    };
};

var RegistrationRetraction = function(selector, submitUrl) {
    this.viewModel = new RegistrationRetractionViewModel(submitUrl);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = RegistrationRetraction;