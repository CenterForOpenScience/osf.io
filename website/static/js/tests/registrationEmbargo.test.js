/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var registrationEmbargo = require('js/registrationEmbargo');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('registrationEmbargo', () => {

    describe('RegistrationEmbargoViewModel', () => {
        var vm;
        var MAKE_PUBLIC = 'immediate';
        var MAKE_EMBARGO = 'embargo';

        beforeEach(() => {
            vm = new registrationEmbargo.ViewModel();
        });

        describe('#checkShowEmbargoDatePicker', () => {
            it('returns false if registrationChoice is make public', () => {
                vm.registrationChoice(MAKE_PUBLIC);
                vm.checkShowEmbargoDatePicker();
                assert.isFalse(vm.showEmbargoDatePicker());
            });
            it('returns true if registrationChoice is make embargo', () => {
                vm.registrationChoice(MAKE_EMBARGO);
                vm.checkShowEmbargoDatePicker();
                assert.isTrue(vm.showEmbargoDatePicker());
            });
        });
        describe('#embargoEndDate', () => {
            it('returns Date from user input', () =>{
                vm.pikaday('2015-01-01');
                var date = vm.embargoEndDate();
                assert.isTrue(date instanceof Date);
            });
        });
        describe('#isEmbargoEndDateValid', () => {
            it('returns true for date more than 2 days but less than 365 days in the future', () => {
                var validDate = new Date();
                validDate.setDate(validDate.getDate() + 3);
                vm.pikaday(validDate);
                assert.isTrue(vm.isEmbargoEndDateValid());
            });
            it('returns false for date less than 2 days in the future', () => {
                var invalidPastDate = new Date();
                invalidPastDate.setDate(invalidPastDate.getDate() - 2);
                vm.pikaday(invalidPastDate);
                assert.isFalse(vm.isEmbargoEndDateValid());
            });
            it('returns false for date more than 4 years in the future', () => {
                var invalidFutureDate = new Date();
                invalidFutureDate.setDate(invalidFutureDate.getDate() + 1460);
                vm.pikaday(invalidFutureDate);
                assert.isFalse(vm.isEmbargoEndDateValid());
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
    });
});

