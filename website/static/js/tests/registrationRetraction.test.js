/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $osf = require('js/osfHelpers');
var utils = require('./utils');

var registrationRetraction = require('js/registrationRetraction');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('registrationRetraction', () => {
    describe('ViewModels', () => {

        describe('RegistrationRetractionViewModel', () => {
            var vm;
            var registrationTitle = 'This is a fake registration';
            var invalidConfirmationText = 'abcd';
            var submitUrl = '/project/abcdef/retraction/';
            var redirectUrl = '/project/abdef/';
            var response = {redirectUrl: redirectUrl};
            var endpoints = [
                {
                    method: 'POST',
                    url: submitUrl,
                    response: response
                }
            ];
            var server;


            before(() => {
                server = utils.createServer(sinon, endpoints);
            });

            after(() => {
                server.restore();
            });

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
                var postSpy;

                beforeEach(() => {
                    growlSpy = new sinon.stub($osf, 'growl');
                    postSpy = new sinon.spy($osf, 'postJSON');
                });

                afterEach(() => {
                    growlSpy.restore();
                    postSpy.restore();
                });

                it('calls growl if invalid confirmation text submitted', () => {
                    vm.confirmationText(invalidConfirmationText);
                    vm.submit();
                    assert.calledOnce(growlSpy);
                    assert.notCalled(postSpy);
                });
                it('submits successfully with valid confirmation text', (done) => {
                    var onSubmitSuccessStub = new sinon.stub(vm, 'onSubmitSuccess');

                    vm.confirmationText(registrationTitle);
                    vm.submit().done(() => {
                        assert.equal(response, redirectUrl)
                        assert.called(onSubmitSuccessStub);
                        assert.called(postSpy);
                        assert.notCalled(growlSpy);
                    });
                    onSubmitSuccessStub.restore();
                    done();
                });
            });
        });
    });
});

