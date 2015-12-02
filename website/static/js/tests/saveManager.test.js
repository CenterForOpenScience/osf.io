/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var SaveManager = require('js/saveManager');
var url = 'http://foo.com';
var sm = new SaveManager(url);

describe('SaveManager', () => {
    var server;
    beforeEach(() => {
        server = sinon.fakeServer.create();
        server.autoRespond = true;
        server.autoRespondAfter = 200;
        server.respondWith(url, '{}');
    });
    afterEach(() => {
        server.restore();
    });

    it('blocks multiple save requests and queues the last request', (done) => {
        var firstSave = sm.save({first: true});
        var secondSave = sm.save({second: true});
        assert.equal(server.requests.length, 1);
        firstSave.always(function() {
            assert.equal(server.queue.length, 1);
            assert.equal(server.requests.length, 2);
        });
        secondSave.always(function() {
            assert.equal(server.queue.length, 0);
            assert.equal(server.requests.length, 2);
            done();
        });
    });    
    it('queues the last made save request if more than one is made while blocking', (done) => {
        var firstSave = sm.save({first: true});
        var secondSave = sm.save({second: true});
        var thirdSave = sm.save({third: true});
        assert.equal(server.requests.length, 1);
        firstSave.always(function() {
            assert.equal(server.queue.length, 1);
            assert.equal(server.requests.length, 2);
        });
        secondSave.always(function() {
            // The second save request does not get resolved
            assert.fail();
        });
        thirdSave.always(function() {
            assert.equal(server.queue.length, 0);
            assert.equal(server.requests.length, 2);
            done();
        });
    });    
    
});
