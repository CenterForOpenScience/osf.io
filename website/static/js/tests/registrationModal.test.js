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
            var validDateTwoDays = new Date(2016, 0, 1);
            vm.pikaday(new Date (2016, 0, 4));
            assert.isTrue(vm.minimumTimeValidation(validDateTwoDays));
        });
        it('returns true for date less than 4 years in the future', () => {
            var validDateFourYears = new Date(2016, 0, 1);
            vm.pikaday(new Date (2019, 11, 30));
            assert.isTrue(vm.maximumTimeValidation(validDateFourYears));
        });
        it('returns false for date less than 2 days in the future', () => {
            var invalidDateTwoDays = new Date(2016, 0, 1);
            vm.pikaday(new Date (2016, 0, 2));
            assert.isFalse(vm.minimumTimeValidation(invalidDateTwoDays));
        });
        it('returns false for date at least 4 years in the future', () => {
            var invalidDateFourYears = new Date(2016, 0, 1);
            vm.pikaday(new Date (2020, 0, 1));
            assert.isFalse(vm.maximumTimeValidation(invalidDateFourYears));
        });
        it('returns true for date more than 2 days in the future, regardless of time zone', () => {
            var validDateTwoDaysTZ = new Date(2016, 0, 1);
            validDateTwoDaysTZ.setMinutes(validDateTwoDaysTZ.getMinutes() - validDateTwoDaysTZ.getTimezoneOffset());
            var validDateTZFuture = new Date(validDateTwoDaysTZ);
            validDateTZFuture.setDate(validDateTwoDaysTZ.getDate() + 3);
            vm.pikaday(validDateTZFuture);
            assert.isTrue(vm.minimumTimeValidation(validDateTwoDaysTZ));
        });
        it('returns true for date less than 4 years in the future, regardless of time zone', () => {
            var validDateFourYearsTZ = new Date(2016, 0, 1);
            validDateFourYearsTZ.setMinutes(validDateFourYearsTZ.getMinutes() - validDateFourYearsTZ.getTimezoneOffset());
            console.log(validDateFourYearsTZ);
            var validDateTZFutureYears = new Date(validDateFourYearsTZ);
            validDateTZFutureYears.setDate(validDateTZFutureYears.getDate() + 1460);
            console.log(validDateTZFutureYears);
            vm.pikaday(validDateTZFutureYears);
            assert.isTrue(vm.maximumTimeValidation(validDateTZFutureYears));
        });
    });
});
