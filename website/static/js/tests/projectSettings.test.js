/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var utils = require('tests/utils');
var faker = require('faker');

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var language = require('js/osfLanguage').projectSettings;

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
    },
    currentUser: {
        fullname: 'John Cena'
    }
};
sinon.stub($, 'ajax', function() {
    var ret = $.Deferred();
    ret.resolve({
        contributors: []
    });
    return ret.promise();
});
var ProjectSettings = require('js/projectSettings.js');
$.ajax.restore();

var ProjectSettings = ProjectSettings.ProjectSettings;

describe('ProjectSettings', () => {
    var category = faker.internet.domainWord();
    var categoryOptions = [];
    for (var i = 0; i < 10; i++) {
        categoryOptions.push(faker.internet.domainWord());
    }
    var updateUrl = faker.internet.ip();
    var vm = new ProjectSettings({category: category, categoryOptions: categoryOptions, updateUrl: updateUrl, node_id: 'nodeID'});
    describe('#constructor', function() {
        it('throws an error if no updateUrl is passed', () => {
            var broken = function() {
                new ProjectSettings({category: category, categoryOptions: categoryOptions});
            };
            assert.throws(broken , language.instantiationErrorMessage);
        });
        it('implements the changeMessage interface', () => {
            assert.isTrue(vm.hasOwnProperty('message'));
            assert.isTrue(vm.hasOwnProperty('messageClass'));
            assert.isTrue(Boolean(vm.changeMessage) || false);
            assert.isTrue(Boolean(vm.resetMessage) || false);
        });
    });
    describe('#updateError', () => {
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
            vm.updateError({}, error, {});
            assert.calledWith(changeMessageSpy, language.updateErrorMessage);
            assert.calledWith(ravenStub, language.updateErrorMessage, {
                url: updateUrl,
                textStatus: error,
                err: {},
            });
        });
    });
    describe('#updateAll', () => {
        var server;
        var serverSpy = sinon.spy();
        before(() => {
            server = sinon.fakeServer.create();
            server.respondWith(
                'PUT',
                updateUrl,
                function(xhr) {
                    serverSpy();
                    xhr.respond(
                        200,
                        {'Content-Type': 'application/json'}
                    );
                }
            );
        });
        after(() => {
            server.restore();
        });
        it('sends a put to the updateUrl with the settings inputs and updates them on success', (done) => {
            var newcategory = categoryOptions[0];
            vm.selectedCategory(newcategory);
            vm.title('New title');
            vm.description('New description');
            vm.requestPayload = vm.serialize();
            vm.updateAll()
                .always(function() {
                    assert.called(serverSpy);
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
        it('restores the category, title, and description to those of the VM, and resets the message', () => {
            vm.selectedCategory(categoryOptions[0]);
            vm.changeMessage('Some message', 'some-class');
            vm.cancelAll();
            assert.equal(vm.selectedCategory(), vm.categoryPlaceholder);
            assert.equal(vm.title(), vm.titlePlaceholder);
            assert.equal(vm.description(), vm.descriptionPlaceholder);
            assert.called(resetMessageSpy);
        });
    });
});
