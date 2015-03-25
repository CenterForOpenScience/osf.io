/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $osf = require('js/osfHelpers');

var registrationRetraction = require('js/registrationRetraction');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('registrationRetraction', () => {
    describe('ViewModels', () => {

        describe('RegistrationRetractionViewModel', () => {
            var vm;
            var registrationTitle = 'This is a fake registration';
            var invalidConfirmationText = 'abcd';
            var submitUrl = 'http://pewpewpew.pew';

            beforeEach(() => {
                vm = new registrationRetraction.ViewModel(submitUrl, registrationTitle);
            });

            it('non-matching registration title is invalid', () => {
                vm.confirmationText(invalidConfirmationText);
                assert.isFalse(vm.confirmationText.isValid());
            });

            it('matching registration title is valid', () => {
                 vm.confirmationText(registrationTitle);
                assert.isTrue(vm.confirmationText.isValid());
            });

            describe('submit', () => {
                var growlSpy;

                beforeEach(() => {
                    growlSpy = new sinon.stub($osf, 'growl');
                });

                afterEach(() => {
                    growlSpy.restore();
                });

                it('growl called if invalid confirmation text submitted', () => {
                    vm.confirmationText(invalidConfirmationText);
                    vm.submit();
                    assert.calledOnce(growlSpy);
                });
                it('growl not called with valid username', () => {
                    vm.confirmationText(registrationTitle);
                    vm.submit();
                    assert.notCalled(growlSpy);
                });
            });
        });
    });
});

