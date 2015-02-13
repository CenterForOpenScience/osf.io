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

    self.justification = ko.observable('').extend({
        required: true,
        minLength: 1
    });

    // TODO(hrybacki): look into contextVars to determine how do grab the project/node title for use here...
    self.confirmationText = ko.observable('').extend({
        required: true,
        mustEqual: 'retract registration'
    });

    // Preserve object of validated fields for use in `submit`
    var validatedFields = {
        justification: self.justfication,
        confirmationText: self.confirmationText
    };

    // Collect validated fields
    self.validatedFields = ko.validatedObservable($.extend({}, validatedFields));

    self.submitted = ko.observable(false);

    // FIXME(hrybacki): not working correctly -- once validated, if user deletes
    // data from a field (making it invalid), is_valid is still true...
    self.isValid = ko.computed(function() {
        return self.validatedFields.isValid();
    });

    self.submit = function() {
        // Show errors if invalid
        if (!self.isValid()) {
            alert('Fix yo shit...');
        }

        // Else Submit
        $osf.postJSON(
            submitUrl,
            ko.toJS(self)
        ).done(function(response){
                $( location ).attr("href", response.redirectUrl);
            }
        ).fail(
            console.log('Unsuccessful submission')
        );
    };

};

var RegistrationRetraction = function(selector, submitUrl) {
    this.viewModel = new RegistrationRetractionViewModel(submitUrl);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = RegistrationRetraction;