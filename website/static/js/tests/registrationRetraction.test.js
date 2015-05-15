/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $osf = require('js/osfHelpers');
var utils = require('./utils');
var Raven = require('raven-js');
var faker = require('faker');

var registrationRetraction = require('js/registrationRetraction');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('registrationRetraction', () => {
    describe('ViewModels', () => {

        describe('RegistrationRetractionViewModel', () => {
            var vm;
            var registrationTitle = 'This is a fake registration';
            var invalidJustification = faker.lorem.paragraphs(50);
            var invalidConfirmationText = 'abcd';
            var submitUrl = '/project/abcdef/retraction/';
            var invalidSubmitUrl = '/notAnEndpoint/';
            var redirectUrl = '/project/abdef/';
            var response = {redirectUrl: redirectUrl};
            var endpoints = [
                {
                    method: 'POST',
                    url: submitUrl,
                    response: response
                },
                {
                    method: 'POST',
                    url: invalidSubmitUrl,
                    response: {},
                    status: 500
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
                it('calls growl if justification is too long', () => {
                    vm.confirmationText(registrationTitle);
                    vm.justification(invalidJustification);
                    vm.submit();
                    assert.calledOnce(growlSpy);
                    assert.notCalled(postSpy);
                });
                it('submits successfully with valid confirmation text', (done) => {
                    var onSubmitSuccessStub = new sinon.stub(vm, 'onSubmitSuccess');

                    vm.confirmationText(registrationTitle);
                    vm.submit().always(() => {
                        assert.equal(response.redirectUrl, redirectUrl);
                        assert.called(onSubmitSuccessStub);
                        assert.called(postSpy);
                        assert.notCalled(growlSpy);
                        onSubmitSuccessStub.restore();
                        done();
                    });
                });

                it('logs error with Raven if submit fails', (done) => {
                    vm = new registrationRetraction.ViewModel(invalidSubmitUrl, registrationTitle);
                    var onSubmitErrorSpy = new sinon.spy(vm, 'onSubmitError');
                    var ravenStub = new sinon.stub(Raven, 'captureMessage');

                    vm.confirmationText(registrationTitle);
                    vm.submit().always((xhr) => {
                        assert.equal(xhr.status, 500);
                        assert.equal(response.redirectUrl, redirectUrl);
                        assert.called(onSubmitErrorSpy);
                        assert.called(postSpy);
                        assert.called(growlSpy);
                        onSubmitErrorSpy.restore();
                        ravenStub.restore();
                        done();
                    });
                });

            });
        });
    });
});

