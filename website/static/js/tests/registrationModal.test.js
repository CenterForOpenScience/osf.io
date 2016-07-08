/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var utils = require('tests/utils');
var faker = require('faker');
var moment = require('moment');

var RegistrationModal = require('js/registrationModal').ViewModel;

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {
    prefix: ''
});

describe('registrationModal', () => {
    sinon.collection.restore();
    var MAKE_PUBLIC = 'immediate';
    var MAKE_EMBARGO = 'embargo';

    var confirm = sinon.stub();
    var vm = new RegistrationModal(
        confirm, 
        [],
        null
    ); 
    beforeEach(() => {
        vm = new RegistrationModal(
            confirm, 
            [],
            null
        );
    });
    afterEach(() => {
        confirm.reset();
    });

    describe('#constructor', () => {
        it('takes a confirm method as a callback for bootbox success', () => {
            var args = {
                registrationChoice: vm.registrationChoice(),
                embargoEndDate: vm.embargoEndDate(),
                minimumTimeValidation: vm.minimumTimeValidation(),
                maximumTimeValidation: vm.maximumTimeValidation()
            };
            vm.register();
            assert.isTrue(confirm.calledWith(args));
        });
        it('takes an optional knockout validator', () => {
            var validate = sinon.spy();
            var instance = new RegistrationModal(
                function() {},
                [],
                {
                    validator: validate,
                    message: 'Bad, bad, bad.'
                }
            );
            var d = new Date();
            d.setDate(d.getDate() + 3);
            instance.pikaday(d);
            instance.pikaday.isValid();
            assert.isTrue(validate.called);
        });
    });
    describe('#embargoEndDate', () => {
        it('returns moment from user input', () => {
            vm.pikaday('2015-01-01');
            var date = vm.embargoEndDate();
            assert.isTrue(date instanceof moment);
        });
    });
    describe('#requestingEmbargo', () => {
        it('is true if the current registrationChoice is embargo', () => {
            vm.registrationChoice(MAKE_EMBARGO);
            assert.isTrue(vm.requestingEmbargo());
            vm.registrationChoice(MAKE_PUBLIC);
            assert.isFalse(vm.requestingEmbargo());
        });
    });
    describe('#pikaday.isValid', () => {             
        it('returns true for date more than 2 days but less than 4 years in the future', () => {
            var validDate = new Date();
            validDate.setDate(validDate.getDate() + 3);
            vm.pikaday(validDate);
            assert.isTrue(vm.pikaday.isValid());
        });
        it('returns false for date less than 2 days in the future', () => {
            var invalidPastDate = new Date();
            invalidPastDate.setDate(invalidPastDate.getDate() - 2);
            vm.pikaday(invalidPastDate);
            assert.isFalse(vm.pikaday.isValid());
        });
        it('returns false for date more than 4 years in the future', () => {
            var invalidFutureDate = new Date();
            invalidFutureDate.setDate(invalidFutureDate.getDate() + 1460);
            vm.pikaday(invalidFutureDate);
            assert.isFalse(vm.pikaday.isValid());
        });
    });
    describe('#requestingEmbargo', () => {
        it('returns false if user chose make public', () => {
            vm.registrationChoice(MAKE_PUBLIC);
            assert.isFalse(vm.requestingEmbargo());
        });
        it('returns true if user chose requests embargo', () => {
            vm.registrationChoice(MAKE_EMBARGO);
            assert.isTrue(vm.requestingEmbargo());
        });
    });
    describe('#timeValidation', () => {
        it('returns true for date more than 2 days in the future', () => {
            var validDateTwoDays = new Date();
            vm.pikaday(new Date (validDateTwoDays.getTime() + 259200000)); //+3 Days
            assert.isTrue(vm.minimumTimeValidation(null, null, validDateTwoDays));
        });
        it('returns true for date less than 4 years in the future', () => {
            var validDateFourYears = new Date();
            vm.pikaday(new Date (validDateFourYears.getTime() + 126057600000)); //+1459 Days
            assert.isTrue(vm.maximumTimeValidation(null, null, validDateFourYears));
        });
        it('returns false for date less than 2 days in the future', () => {
            var invalidDateTwoDays = new Date();
            vm.pikaday(new Date (invalidDateTwoDays.getTime() + 86400000)); //+1 Day
            assert.isFalse(vm.minimumTimeValidation(null, null, invalidDateTwoDays));
        });
        it('returns false for date at least 4 years in the future', () => {
            var invalidDateFourYears = new Date();
            vm.pikaday(new Date (invalidDateFourYears.getTime() + 126144000000)); //+1460 Days
            assert.isFalse(vm.maximumTimeValidation(null, null, invalidDateFourYears));
        });
        it('returns true for date more than 2 days in the future, in a western timezone', () => {
            var validDateTwoDaysTZWest = moment().utcOffset(-4).toDate();
            validDateTwoDaysTZWest.setMinutes(validDateTwoDaysTZWest.getMinutes() - validDateTwoDaysTZWest.getTimezoneOffset());
            var validDateTZFutureWest = new Date(validDateTwoDaysTZWest);
            validDateTZFutureWest.setDate(validDateTwoDaysTZWest.getDate() + 3);
            vm.pikaday(validDateTZFutureWest);
            assert.isTrue(vm.minimumTimeValidation(null, null, validDateTwoDaysTZWest));
        });
        it('returns true for date more than 2 days in the future, in an eastern timezone', () => {
            var validDateTwoDaysTZEast = moment().utcOffset(4).toDate();
            validDateTwoDaysTZEast.setMinutes(validDateTwoDaysTZEast.getMinutes() - validDateTwoDaysTZEast.getTimezoneOffset());
            var validDateTZFutureEast = new Date(validDateTwoDaysTZEast);
            validDateTZFutureEast.setDate(validDateTwoDaysTZEast.getDate() + 3);
            vm.pikaday(validDateTZFutureEast);
            assert.isTrue(vm.minimumTimeValidation(null, null, validDateTwoDaysTZEast));
        });
        it('returns true for date less than 4 years in the future, in a western timezone', () => {
            var validDateFourYearsTZWest = moment().utcOffset(-4).toDate();
            validDateFourYearsTZWest.setMinutes(validDateFourYearsTZWest.getMinutes() - validDateFourYearsTZWest.getTimezoneOffset());
            var validDateTZFutureWest = new Date(validDateFourYearsTZWest);
            validDateTZFutureWest.setDate(validDateFourYearsTZWest.getDate() + 1459);
            vm.pikaday(validDateTZFutureWest);
            assert.isTrue(vm.maximumTimeValidation(null, null, validDateFourYearsTZWest));
        });
        it('returns true for date less than 4 years in the future, in an eastern timezone', () => {
            var validDateFourYearsTZEast = moment().utcOffset(4).toDate();
            validDateFourYearsTZEast.setMinutes(validDateFourYearsTZEast.getMinutes() - validDateFourYearsTZEast.getTimezoneOffset());
            var validDateTZFutureEastFY = new Date(validDateFourYearsTZEast);
            validDateTZFutureEastFY.setDate(validDateFourYearsTZEast.getDate() + 1459);
            vm.pikaday(validDateTZFutureEastFY);
            assert.isTrue(vm.maximumTimeValidation(null, null, validDateFourYearsTZEast));
        });
    });
});
