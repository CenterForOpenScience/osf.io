/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var faker = require('faker');

var utils = require('./utils');
var profile = require('../profile');

var assign = require('object-assign');

/**
 * Utility to create a fake server with sinon.
 */
var defaultHeaders = {'Content-Type': 'application/json'};
function createServer(endpoints) {
    var server = sinon.fakeServer.create();
    for (var url in endpoints) {
        var endpoint = endpoints[url];
        var headers = assign(
            {},
            defaultHeaders,
            endpoints.headers
        );
        server.respondWith(
            endpoint.method || 'GET',
            url,
            [
                endpoint.status || 200,
                headers,
                JSON.stringify(endpoint.response)
            ]
        );
    }
    return server;
}

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('ViewModels', () => {

    var nameURLs = {
        crud: '/settings/names/',
        impute: '/settings/names/impute/'
    };
    var vm, server;

    var names = {
        full: faker.name.findName(),
        given: faker.name.firstName(),
        middle: [faker.name.lastName()],
        family: faker.name.lastName(),
        suffix: faker.name.suffix()
    };

    before(() => {
        // Set up fake server
        var endpoints = {};

        // Set up responses for names URLs
        endpoints[nameURLs.crud]  = {
            response: names
        };
        endpoints[nameURLs.impute] = {
            response: names
        };

        server = utils.createServer(endpoints);
    });

    after(() => {
        server.restore();
    });


    describe('NameViewModel', () => {
        it('should fetch and update names upon instantiation', (done) => {
            var vm = new profile._NameViewModel(nameURLs, ['view', 'edit'], function() {
                // Observables have been updated
                assert.equal(this.full(), names.full);
                assert.equal(this.given(), names.given);
                assert.equal(this.family(), names.family);
                assert.equal(this.suffix(), names.suffix);
                done();
            });
            window.onbeforeunload = null; // hack to disable BaseViewModel's onbeforeunload handler
            server.respond();
        });

        describe('impute', () => {
            it('should send request and update imputed names', () => {

            });
        });
    });
});
