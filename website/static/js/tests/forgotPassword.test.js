/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $osf = require('js/osfHelpers');

var forgotPassword = require('js/forgotPassword');
var formViewModel = require('js/formViewModel');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe.skip('forgotPassword', () => {
    describe('ViewModels', () => {

        describe('ForgtoPasswordViewModel', () => {
            var vm;

            var invalidUsername = 'notanemail';
            var validUsername = 'tim@tom.com';

            beforeEach(() => {
                vm = new forgotPassword.ViewModel();
            });

            it('inherit from FormViewModel', () => {
                assert.instanceOf(vm, formViewModel.FormViewModel);
            });

            it('invalid email is not valid', () => {
                vm.username(invalidUsername);
                assert.isFalse(vm.username.isValid());
            });

            it('valid email is valid', () => {
                vm.username(validUsername);
                assert.isTrue(vm.username.isValid());
            });

            describe('submit', () => {
                var growlSpy;

                beforeEach(() => {
                    growlSpy = new sinon.stub($osf, 'growl');
                });

                afterEach(() => {
                    growlSpy.restore();
                });

                it('growl called if invalid username submitted', () => {
                    vm.username(invalidUsername);
                    vm.submit();
                    assert.isTrue(growlSpy.calledOnce);
                });
                it('growl not called with valid username', () => {
                    vm.username(validUsername);
                    vm.submit();
                    assert.isFalse(growlSpy.called);
                });
            });
        });
    });
});

