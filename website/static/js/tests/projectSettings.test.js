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

var NodeCategoryTitleDescriptionSettings = ProjectSettings.NodeCategoryTitleDescriptionSettings;

describe('NodeCategoryTitleDescriptionSettings', () => {
    var category = faker.internet.domainWord();
    var categories = [];
    for (var i = 0; i < 10; i++) {
        categories.push(faker.internet.domainWord());
    }
    var updateUrl = faker.internet.ip();
    var vm = new NodeCategoryTitleDescriptionSettings(category, categories, updateUrl);
    describe('#constructor', function() {
        it('throws an error if no updateUrl is passed', () => {
            var broken = function() {
                new NodeCategoryTitleDescriptionSettings(category, categories);
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
    describe('#updateCategorySuccess', () => {
        var changeMessageSpy;
        before(() => {
            changeMessageSpy = sinon.spy(vm, 'changeMessage');
        });
        after(() => {
            vm.changeMessage.restore();
        });
        it('updates the message, updates the category, and sets the dirty state to false', () => {
            var newcategory = categories[0];
            vm.updateCategorySuccess(newcategory);
            assert.calledWith(changeMessageSpy, vm.UPDATE_SUCCESS_MESSAGE, vm.MESSAGE_SUCCESS_CLASS);
            assert.equal(newcategory, vm.category());
            assert.isFalse(vm.dirty());
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
            assert.calledWith(changeMessageSpy, vm.UPDATE_ERROR_MESSAGE, vm.MESSAGE_ERROR_CLASS);
            assert.calledWith(ravenStub, vm.UPDATE_ERROR_MESSAGE_RAVEN, {
                url: updateUrl,
                textStatus: error,
                err: {}
            });
        });
    });
    describe('#updateCategory', () => {
        var server;
        var serverSpy = sinon.spy();
        var updateSuccessSpy = sinon.spy(vm, 'updateCategorySuccess');
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
            var newcategory = categories[0];
            vm.selectedCategory(newcategory);
            vm.updateCategory()
                .always(function() {
                    assert.called(serverSpy);
                    assert.calledWith(updateSuccessSpy, newcategory);
                    done();
                });
            server.respond();
        });
    });
    describe('#cancelUpdateCategory', () => {
        var resetMessageSpy;
        before(() => {
            resetMessageSpy = sinon.spy(vm, 'resetMessage');
        });
        after(() => {
            vm.resetMessage.restore();
        });
        it('restores the selectedCategory to the VM\'s category, sets the dirty state to false, and resets the message', () => {
            vm.selectedCategory(categories[0]);
            vm.dirty(true);
            vm.changeMessage('Some message', 'some-class');
            vm.cancelUpdateCategory();
            assert.equal(vm.selectedCategory(), vm.category());
            assert.isFalse(vm.dirty());
            assert.called(resetMessageSpy);
        });
    });
});
