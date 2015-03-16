/**
 * On page load, focuses on justification input and
 * maintains knockout ViewModel
**/
'use strict';

var ko = require('knockout');
require('knockout-validation');
var $ = require('jquery');

var $osf = require('js/osfHelpers');

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
    self.justification = ko.observable('');
    self.confirmationText = ko.observable().extend({
        required: true,
        mustEqual: self.registrationTitle
    });

    self.submit = function() {
        // Show errors if invalid
        if (!self.confirmationText.isValid()) {
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

module.exports = {
    RegistrationRetraction: RegistrationRetraction,
    ViewModel: RegistrationRetractionViewModel
};