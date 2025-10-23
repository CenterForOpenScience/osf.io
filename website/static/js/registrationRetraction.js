/**
 * On page load, maintains knockout ViewModel
**/
'use strict';

var $osf = require('js/osfHelpers');

var ko = require('knockout');
require('knockout.validation');

var ChangeMessageMixin = require('js/changeMessage');
var oop = require('js/oop');
var Raven = require('raven-js');

var RegistrationRetractionViewModel = oop.extend(
    ChangeMessageMixin,
    {
        constructor: function(submitUrl) {
            this.super.constructor.call(this);

            ko.validation.registerExtenders();

            var self = this;

            self.submitUrl = submitUrl;

            self.confirmationString = $osf.getConfirmationString();
            self.justification = ko.observable('').extend({
                maxLength: 2048
            });
            self.confirmationText = ko.observable().extend({
                required: true,
                mustEqual: self.confirmationString
            });
            self.disableSave = ko.observable(false);
            self.valid = ko.computed(function(){
                return !self.disableSave() && self.confirmationText.isValid();
            });
        },
        SUBMIT_ERROR_MESSAGE: 'Error submitting your withdrawal request, please try again. If the problem ' +
                'persists, email ' + $osf.osfSupportLink(),
        CONFIRMATION_ERROR_MESSAGE: 'Please enter the registration title before clicking Withdraw Registration',
        JUSTIFICATION_ERROR_MESSAGE: 'Your justification is too long, please enter a justification with no more ' +
            'than 2048 characters long.',
        MESSAGE_ERROR_CLASS: 'text-danger',
        onSubmitSuccess: function(response) {
            window.location = response.redirectUrl;
        },
        onSubmitError: function(xhr, status, errorThrown) {
            var self = this;
            self.disableSave(false);
            self.changeMessage(self.SUBMIT_ERROR_MESSAGE, self.MESSAGE_ERROR_CLASS);
            Raven.captureMessage('Could not submit registration withdrawal.', {
                extra: {
                    xhr: xhr,
                    status: status,
                    error: errorThrown
                }
            });
        },
        submit: function() {
            var self = this;
            self.disableSave(true);
            // Show errors if invalid
            if (!self.confirmationText.isValid()) {
                self.changeMessage(self.CONFIRMATION_ERROR_MESSAGE, self.MESSAGE_ERROR_CLASS);
                return false;
            } else if (!self.justification.isValid()) {
                self.changeMessage(self.JUSTIFICATION_ERROR_MESSAGE, self.MESSAGE_ERROR_CLASS);
                return false;
            } else {
                // Else Submit
                return $osf.postJSON(self.submitUrl, ko.toJS(self))
                    .done(self.onSubmitSuccess.bind(self))
                    .fail(self.onSubmitError.bind(self));
            }
        }
});

var RegistrationRetraction = function(selector, submitUrl) {
    this.viewModel = new RegistrationRetractionViewModel(submitUrl);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    RegistrationRetraction: RegistrationRetraction,
    ViewModel: RegistrationRetractionViewModel
};
