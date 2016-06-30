var ko = require('knockout');
var moment = require('moment');
var pikaday = require('pikaday');
require('pikaday-css');
var bootbox = require('bootbox');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var language = require('js/osfLanguage').registrations;

var template = require('raw!templates/registration-modal.html');
$(document).ready(function() {
    $('body').append(template);
});

var MAKE_PUBLIC = {
    value: 'immediate',
    message: 'Make registration public immediately'
};
var MAKE_EMBARGO = {
    value: 'embargo',
    message: 'Enter registration into embargo'
};
var utcOffset = moment().utcOffset();
var today = new Date();
var todayMinimum = moment().add(2, 'days');
var todayMaximum = moment().add(4, 'years');

var RegistrationViewModel = function(confirm, prompts, validator) {

    var self = this;

    self.registrationOptions = [
        MAKE_PUBLIC,
        MAKE_EMBARGO
    ];
    self.registrationChoice = ko.observable(MAKE_PUBLIC.value);

    self.pikaday = ko.observable(today);
    var picker = new pikaday(
        {
            bound: true,
            field: document.getElementById('endDatePicker'),
            onSelect: function() {
                self.pikaday(picker.toString());
                self.isEmbargoEndDateValid();
            }
        }
    );
    self.embargoEndDate = ko.computed(function() {
        return moment(new Date(self.pikaday())).subtract(utcOffset, 'minutes');
    });

    self.minimumTimeValidation = function (x, y, embargoLocalDateTime) {
        var minEmbargoMoment = getMinimumDate(embargoLocalDateTime),
            endEmbargoMoment = self.embargoEndDate();
        return minEmbargoMoment.isBefore(endEmbargoMoment) && endEmbargoMoment.isSameOrAfter(todayMinimum);
    };

    self.maximumTimeValidation = function (x, y, embargoLocalDateTime) {
        var maxEmbargoMoment = getMaximumDate(embargoLocalDateTime),
            endEmbargoMoment = self.embargoEndDate();
        return maxEmbargoMoment.isAfter(endEmbargoMoment) && endEmbargoMoment.isSameOrBefore(todayMaximum);
    };

    var validation = [{
        validator: self.minimumTimeValidation,
        message: 'Embargo end date must be at least three days in the future.'
    }, {
        validator: self.maximumTimeValidation,
        message: 'Embargo end date must be less than four years in the future.'
    }];
    if(validator) {
        validation.unshift(validator);
    }
    self.pikaday.extend({
        validation: validation
    });

    self.showEmbargoDatePicker = ko.observable(false);
    self.requestingEmbargo = ko.computed(function() {
        var choice = self.registrationChoice();
        return choice === MAKE_EMBARGO.value;
    });
    self.requestingEmbargo.subscribe(function(requestingEmbargo) {
        self.showEmbargoDatePicker(requestingEmbargo);
    });

    self.canRegister = ko.pureComputed(function() {
        if (self.requestingEmbargo()) {
            return self.pikaday.isValid();
        }
        return true;
    });

    self.confirm = confirm;
    self.preRegisterPrompts = prompts;
    self.close = bootbox.hideAll;
};
RegistrationViewModel.prototype.show = function() {
    var self = this;
    bootbox.dialog({
        size: 'large',
        title: language.registerConfirm,
        message: function() {
            ko.renderTemplate('registrationChoiceModal', self, {}, this);
        }
    });
};
RegistrationViewModel.prototype.register = function() {
    this.confirm({
        registrationChoice: this.registrationChoice(),
        embargoEndDate: this.embargoEndDate(),
        minimumTimeValidation: this.minimumTimeValidation(),
        maximumTimeValidation: this.maximumTimeValidation()
    });
};

module.exports = {
    ViewModel: RegistrationViewModel
};

function getMinimumDate(embargoLocalDateTime) {
    return moment(embargoLocalDateTime).add(2, 'days');
}

function getMaximumDate(embargoLocalDateTime) {
    return moment(embargoLocalDateTime).add(4, 'years').subtract(1, 'days');
}