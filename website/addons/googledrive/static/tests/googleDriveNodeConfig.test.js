/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');
var nodeConfig = require('../googleDriveNodeConfig');

describe('googleDriveNodeConfig', () => {
    var response = {
        result: {
            ownerName: faker.name.findName(),
            userisOwner: true,
            userHasAuth: true,
            validCredentials: true,
            nodeHasAuth: true,
            folder: {name: 'My Documents'},
            urls: {
                owner: '/abc123/',
                config: '/api/v1/12345/googledrive/config/'
            }
        },
        message: 'Successfully updated settings.'
    };
    var endpoints = [
        {
            method: 'GET',
            url: '/api/v1/12345/googledrive/config/',
            response: response
        },
        {
            method: 'PUT',
            url: '/api/v1/12345/googledrive/config/',
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

    describe('ViewModel', () => {
        // Regression test for https://trello.com/c/JRv0kllJ
        it('resets selection after folder selection is submitted', (done) => {
            var vm = new nodeConfig._ViewModel('/api/v1/12345/googledrive/config/');
            vm.selected({id: 'lol', name: '/My Documents', path: '/My Documents'});
            vm.urls({config: '/api/v1/12345/googledrive/config/'});
            vm.submitSettings().done(() => {
                assert.isNull(vm.selected());
                done();
            });
        });
    });

});
