/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var utils = require('tests/utils');
var faker = require('faker');

var $osf = require('js/osfHelpers');
var Raven = require('raven-js');

/*
 * Dear sloria,
 *
 * I'm sorry for injecting globals. Please forgive me.
 *
 * Yours truly,
 * samchrisinger
 */
window.contextVars = {
    node: {
        urls: {
            api: faker.internet.ip()
        }
    }
};

var ProjectSettings = require('js/projectSettings.js');

var ProjectSettings= ProjectSettings.ProjectSettings;

describe('ProjectSettings', () => {
    var category = faker.internet.domainWord();
    var categoryOptions = [];
    for (var i = 0; i < 10; i++) {
        categoryOptions.push(faker.internet.domainWord());
    }
    var updateUrl = faker.internet.ip();
    var vm = new ProjectSettings({category: category, categoryOptions: categoryOptions, updateUrl: updateUrl});
    describe('#constructor', function() {
        it('throws an error if no updateUrl is passed', () => {
            var broken = function() {
                new ProjectSettings({category: category, categoryOptions: categoryOptions});
            };
            assert.throws(broken , vm.INSTANTIATION_ERROR_MESSAGE);
        });
        it('implements the changeMessage interface', () => {
            assert.isTrue(vm.hasOwnProperty('message'));
            assert.isTrue(vm.hasOwnProperty('messageClass'));
            assert.isTrue(Boolean(vm.changeMessage) || false);
            assert.isTrue(Boolean(vm.resetMessage) || false);
        });
    });
    describe('#updateSuccess', () => {
        var changeMessageSpy;
        before(() => {
            changeMessageSpy = sinon.spy(vm, 'changeMessage');
        });
        after(() => {
            vm.changeMessage.restore();
        });
        it('updates the message', () => {
            vm.updateSuccess();
            assert.calledWith(changeMessageSpy, vm.UPDATE_SUCCESS_MESSAGE, vm.MESSAGE_SUCCESS_CLASS);
        });
    });
    describe('#updateCategoryError', () => {
        var changeMessageSpy;
        var ravenStub;
        before(() => {
            changeMessageSpy = sinon.spy(vm, 'changeMessage');
            ravenStub = sinon.stub(Raven, 'captureMessage');
        });
        after(() => {
            vm.changeMessage.restore();
            Raven.captureMessage.restore();
        });
        it('updates the message, and captures the error with Raven', () => {
            var error = faker.lorem.sentence();
            vm.updateCategoryError({}, error, {});
            assert.calledWith(changeMessageSpy, vm.UPDATE_CATEGORY_ERROR_MESSAGE, vm.MESSAGE_ERROR_CLASS);
            assert.calledWith(ravenStub, vm.UPDATE_CATEGORY_ERROR_MESSAGE_RAVEN, {
                url: updateUrl,
                textStatus: error,
                err: {},
            });
        });
    });
    describe('#updateDescriptionError', () => {
        var changeMessageSpy;
        before(() => {
            changeMessageSpy = sinon.spy(vm, 'changeMessage');
        });
        after(() => {
            vm.changeMessage.restore();
        });
        it('updates the message', () => {
            vm.updateDescriptionError();
            assert.calledWith(changeMessageSpy, vm.UPDATE_DESCRIPTION_ERROR_MESSAGE, vm.MESSAGE_ERROR_CLASS);
        });
    });
    describe('#updateCategory', () => {
        var server;
        var serverSpy = sinon.spy();
        var updateTitleSpy = sinon.spy(vm, 'updateTitle');
        before(() => {
            server = sinon.fakeServer.create();
            server.respondWith(
                'PUT',
                updateUrl,
                function(xhr) {
                    serverSpy();
                    var response = {
                        'updated_fields': JSON.parse(xhr.requestBody)
                    };
                    xhr.respond(
                        200,
                        {'Content-Type': 'application/json'},
                        JSON.stringify(response)
                    );
                }
            );
        });
        after(() => {
            server.restore();
        });
        it('sends a put to the updateUrl with the selected category, and updates the category on success', (done) => {
            var newcategory = categoryOptions[0];
            vm.selectedCategory(newcategory);
            vm.updateCategory()
                .always(function() {
                    assert.called(serverSpy);
                    assert.calledWith(updateTitleSpy, newcategory);
                    done();
                });
            server.respond();
        });
    });
    describe('#updateTitle', () => {
        var server;
        var serverSpy = sinon.spy();
        var updateDescriptionSpy = sinon.spy(vm, 'updateDescription');
        before(() => {
            server = sinon.fakeServer.create();
            server.respondWith(
                'PUT',
                updateUrl,
                function(xhr) {
                    serverSpy();
                    var response = {
                        'updated_fields': JSON.parse(xhr.requestBody)
                    };
                    xhr.respond(
                        200,
                        {'Content-Type': 'application/json'},
                        JSON.stringify(response)
                    );
                }
            );
        });
        after(() => {
            server.restore();
        });
        it('sends a put to the updateUrl with user input, and updates the project title on success', (done) => {
            vm.title('New title');
            vm.updateTitle()
                .always(function() {
                    assert.called(serverSpy);
                    assert.calledWith(updateDescriptionSpy);
                    done();
                });
            server.respond();
        });
    });
    describe('#updateDescription', () => {
        var server;
        var serverSpy = sinon.spy();
        var updateSuccessSpy = sinon.spy(vm, 'updateSuccess');
        before(() => {
            server = sinon.fakeServer.create();
            server.respondWith(
                'PUT',
                updateUrl,
                function(xhr) {
                    serverSpy();
                    var response = {
                        'updated_fields': JSON.parse(xhr.requestBody)
                    };
                    xhr.respond(
                        200,
                        {'Content-Type': 'application/json'},
                        JSON.stringify(response)
                    );
                }
            );
        });
        it('sends a put to the updateUrl with user input, and updates the project description on success', (done) => {
            vm.description('New description');
            vm.updateDescription()
                .always(function() {
                    assert.called(serverSpy);
                    assert.calledWith(updateSuccessSpy);
                    done();
                });
            server.respond();
        });
    });
    describe('#cancelAll', () => {
        var resetMessageSpy;
        before(() => {
            resetMessageSpy = sinon.spy(vm, 'resetMessage');
        });
        after(() => {
            vm.resetMessage.restore();
        });
        it('restores the selectedCategory, title, and description to those of the VM, and resets the message', () => {
            vm.selectedCategory(categoryOptions[0]);
            vm.changeMessage('Some message', 'some-class');
            vm.cancelAll();
            assert.equal(vm.selectedCategory(), vm.category);
            assert.equal(vm.title(), vm.decodedTitle);
            assert.equal(vm.description(), vm.decodedDescription);
            assert.called(resetMessageSpy);
        });
    });
});
