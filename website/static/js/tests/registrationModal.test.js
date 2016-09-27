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
            var end = vm.embargoEndDate();
            var args = {
                registrationChoice: vm.registrationChoice(),
                embargoEndDate: end,
                embargoIsLongEnough: vm.embargoIsLongEnough(end),
                embargoIsShortEnough: vm.embargoIsShortEnough(end)
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
            instance.embargoEndDate.isValid();
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
    describe('#embargoEndDate.isValid', () => {
        it('returns true for date more than 2 days but less than 4 years in the future', () => {
            var validDate = new Date();
            validDate.setDate(validDate.getDate() + 3);
            vm.pikaday(validDate);
            assert.isTrue(vm.embargoEndDate.isValid());
        });
        it('returns false for date less than 2 days in the future', () => {
            var invalidPastDate = new Date();
            invalidPastDate.setDate(invalidPastDate.getDate() - 2);
            vm.pikaday(invalidPastDate);
            assert.isFalse(vm.embargoEndDate.isValid());
        });
        it('returns false for date more than 4 years in the future', () => {
            var invalidFutureDate = new Date();
            invalidFutureDate.setDate(invalidFutureDate.getDate() + 1462);
            vm.pikaday(invalidFutureDate);
            assert.isFalse(vm.embargoEndDate.isValid());
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
            var d = new Date();
            vm.pikaday(new Date(d.getTime() + 259200000)); //+3 Days
            vm._now = function() { return moment(d); };
            assert.isTrue(vm.embargoIsLongEnough(vm.embargoEndDate()));
        });
        it('returns true for date less than 4 years in the future', () => {
            var d = new Date();
            vm.pikaday(new Date(d.getTime() + 126057600000)); //+1459 Days
            vm._now = function() { return moment(d); };
            assert.isTrue(vm.embargoIsShortEnough(vm.embargoEndDate()));
        });
        it('returns false for date less than 2 days in the future', () => {
            var d = new Date();
            vm.pikaday(new Date(d.getTime() + 86400000)); //+1 Day
            vm._now = function() { return moment(d); };
            assert.isFalse(vm.embargoIsLongEnough(vm.embargoEndDate()));
        });
        it('returns false for date at least 4 years in the future', () => {
            var d = new Date();
            vm.pikaday(new Date (d.getTime() + 126144000000)); //+1460 Days
            vm._now = function() { return moment(d); };
            assert.isFalse(vm.embargoIsShortEnough(vm.embargoEndDate()));
        });
        it('returns true for date more than 2 days in the future, in a western timezone', () => {
            var d = moment().utcOffset(-4).toDate();
            d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
            var d2 = new Date(d); d2.setDate(d.getDate() + 3); vm.pikaday(d2);
            vm._now = function() { return moment(d); };
            assert.isTrue(vm.embargoIsLongEnough(vm.embargoEndDate()));
        });
        it('returns true for date more than 2 days in the future, in an eastern timezone', () => {
            var d = moment().utcOffset(4).toDate();
            d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
            var d2 = new Date(d); d2.setDate(d.getDate() + 3); vm.pikaday(d2);
            vm._now = function() { return moment(d); };
            assert.isTrue(vm.embargoIsLongEnough(vm.embargoEndDate()));
        });
        it('returns true for date less than 4 years in the future, in a western timezone', () => {
            var d = moment().utcOffset(-4).toDate();
            d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
            var d2 = new Date(d); d2.setDate(d.getDate() + 1459); vm.pikaday(d2);
            vm._now = function() { return moment(d); };
            assert.isTrue(vm.embargoIsShortEnough(vm.embargoEndDate()));
        });
        it('returns true for date less than 4 years in the future, in an eastern timezone', () => {
            var d = moment().utcOffset(4).toDate();
            d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
            var d2 = new Date(d); d2.setDate(d.getDate() + 1459); vm.pikaday(d2);
            vm._now = function() { return moment(d); };
            assert.isTrue(vm.embargoIsShortEnough(vm.embargoEndDate()));
        });
    });
});
