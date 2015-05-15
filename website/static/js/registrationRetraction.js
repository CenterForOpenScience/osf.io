/**
 * On page load, maintains knockout ViewModel
**/
'use strict';

var ko = require('knockout');
require('knockout.validation');
var $ = require('jquery');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');
var koHelpers = require('js/koHelpers');

var RegistrationRetractionViewModel = function(submitUrl, registrationTitle) {

    var self = this;

    self.registrationTitle = registrationTitle;
    self.justification = ko.observable('').extend({
        maxLength: 2048
    });
    self.confirmationText = ko.observable().extend({
        required: true,
        mustEqual : self.registrationTitle
    });
    self.onSubmitSuccess = function(response) {
        window.location = response.redirectUrl;
    };
    self.onSubmitError = function(xhr, status, errorThrown) {
        $osf.growl(
            'Error',
            errorThrown,
            'warning'
        );
        Raven.captureMessage('Could not submit registration retraction.', {
            xhr: xhr,
            status: status,
            error: errorThrown
        });
    };

    self.submit = function() {
        // Show errors if invalid
        if (!self.confirmationText.isValid() || !self.justification.isValid()) {
            $osf.growl(
                'Error',
                'Please enter the registration title before clicking Retract Registration',
                'warning'
            );
            return false;
        } else {
            // Else Submit
            return $osf.postJSON(submitUrl, ko.toJS(self))
                .done(self.onSubmitSuccess)
                .fail(self.onSubmitError);
        }
    };
};

var RegistrationRetraction = function(selector, submitUrl, registrationTitle) {
    this.viewModel = new RegistrationRetractionViewModel(submitUrl, registrationTitle);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    RegistrationRetraction: RegistrationRetraction,
    ViewModel: RegistrationRetractionViewModel
};