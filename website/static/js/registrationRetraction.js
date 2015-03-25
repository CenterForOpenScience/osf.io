/**
 * On page load, maintains knockout ViewModel
**/
'use strict';

var ko = require('knockout');
require('knockout.validation');
var $ = require('jquery');

var $osf = require('js/osfHelpers');
var koHelpers = require('js/koHelpers');

var RegistrationRetractionViewModel = function(submitUrl, registrationTitle) {

    var self = this;
    var mustEqual = koHelpers.mustEqual;

    self.registrationTitle = registrationTitle;
    self.justification = ko.observable('');
    self.confirmationText = ko.observable().extend({
        required: true,
        mustEqual : self.registrationTitle
    });

    self.submit = function() {
        // Show errors if invalid
        if (!self.confirmationText.isValid()) {
            $osf.growl(
                'Error',
                'Please enter the registration title before clicking Retract Registration',
                'warning'
            );
            return false;
        } else {
            // Else Submit
            $osf.postJSON(
                submitUrl,
                ko.toJS(self)
            ).done(function (response) {
                    window.location = response.redirectUrl;
                }
            );
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