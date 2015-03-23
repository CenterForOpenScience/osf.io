/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');
var AddonNodeConfigVM = require('js/addonNodeConfig')._AddonNodeConfigViewModel;

describe('addonNodeConfig', () => {
    var endpoints = [
        {
            method: 'GET',
            url: '/api/v1/12345/addon/config/',
            response: {
                result: {
                    ownerName: faker.name.findName(),
                    userisOwner: true,
                    userHasAuth: true,
                    validCredentials: true,
                    nodeHasAuth: true,
                    urls: {
                        owner: '/abc123/',
                        config: '/api/v1/12345/addon/config/'
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
    });

});
