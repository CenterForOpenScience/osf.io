var ko = require('knockout');

var RegistrationEmbargoViewModel = function() {

    var self = this;

    var today = new Date();
    var TWO_DAYS_FROM_TODAY_TIMESTAMP = new Date().getTime() + (2 * 24 * 60 * 60 * 1000);
    var ONE_YEAR_FROM_TODAY_TIMESTAMP = new Date().getTime() + (365 * 24 * 60 * 60 * 1000);

    self.registrationChoice = ko.observable();
    self.dayChoice = ko.observable();
    self.monthChoice = ko.observable();
    self.yearChoice = ko.observable();

    self.registrationOptions = ko.observableArray([
        'Make registration public immediately',
        'Enter registration into embargo'
    ]);
    self.dayOptions = ko.computed(function() {
        var num_of_days;

        if (['January', 'March', 'May', 'July', 'August', 'October', 'December'].indexOf(self.monthChoice()) > -1) {
            num_of_days = 31;
        } else if (['April', 'June', 'September', 'November'].indexOf(self.monthChoice()) > -1) {
            num_of_days = 30;
        } else { num_of_days = 28; }

        var days = [];
        for (var i=1; i<=num_of_days; i+=1) {
            days.push(i);
        }
        return days;
    });
    self.monthOptions = ko.observableArray([
        'January',
        'February',
        'March',
        'April',
        'May',
        'June',
        'July',
        'August',
        'September',
        'October',
        'November',
        'December'
    ]);
    self.yearOptions = ko.computed(function() {
        return [today.getFullYear(), today.getFullYear() + 1];
    });
    self.showEmbargoDatePicker = ko.observable(false);
    self.checkShowEmbargoDatePicker = function() {
        if (self.registrationChoice()[0] === 'Enter registration into embargo') {
            self.showEmbargoDatePicker(true);
        } else {
            self.showEmbargoDatePicker(false);
        }
    };
    self.embargoEndDate = ko.computed(function() {
        var year = self.yearChoice();
        var month = self.monthOptions().indexOf(self.monthChoice());
        var day = self.dayChoice();
        return new Date(year, month, day);
    });
    self.isEmbargoEndDateValid = ko.computed(function() {
        var endEmbargoDateTimestamp = self.embargoEndDate().getTime();
        if (endEmbargoDateTimestamp < ONE_YEAR_FROM_TODAY_TIMESTAMP && endEmbargoDateTimestamp > TWO_DAYS_FROM_TODAY_TIMESTAMP) {
            return true;
        } else { return false; }
    });
    self.requestingEmbargo = ko.computed(function() {
        var choice = self.registrationChoice();
        if (choice) { return choice[0] === 'Enter registration into embargo'; }
    });
};

var RegistrationEmbargo = function(selector) {
    this.viewModel = new RegistrationEmbargoViewModel();
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    RegistrationEmbargo: RegistrationEmbargo,
    ViewModel: RegistrationEmbargoViewModel
};