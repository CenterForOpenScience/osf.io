/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');
var dropboxNodeConfig = require('../dropboxNodeConfig');

describe('dropboxNodeConfig', () => {
    var endpoints = [
        {
            method: 'GET',
            url: '/api/v1/12345/dropbox/config/',
            response: {
                result: {
                    ownerName: faker.name.findName(),
                    userisOwner: true,
                    userHasAuth: true,
                    validCredentials: true,
                    nodeHasAuth: true,
                    urls: {
                        owner: '/abc123/',
                        config: '/api/v1/12345/dropbox/config/'
                    }
                }
            }
        }
    ];

    var server;
    before(() => {
        server = utils.createServer(sinon, endpoints);
    });

    after(() => {
        server.restore();
    });

    describe('ViewModel', () => {
        it('fetches data from the server on initialization', (done) => {
            var vm = new dropboxNodeConfig._ViewModel('/api/v1/12345/dropbox/config/', '', '', function() {
                // VM is updated with data from the fake server
                var expected = endpoints[0].response.result;
                assert.equal(vm.ownerName(), expected.ownerName);
                assert.equal(vm.nodeHasAuth(), expected.nodeHasAuth);
                assert.equal(vm.userHasAuth(), expected.userHasAuth);
                assert.deepEqual(vm.urls(), expected.urls);
                done();
            });
        });
    });

});
