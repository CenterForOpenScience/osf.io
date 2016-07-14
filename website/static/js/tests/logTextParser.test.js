'use strict';
var assert = require('chai').assert;
var logTextParser = require('js/logTextParser.js');

describe('logTextParser', () => {
    describe('Convert to relative urls', () => {
        var testData = {
            externalAbsoluteUrl: 'http://externaldomin.com/some/external/path/',
            internalAbsoluteUrl: window.location.origin + '/mst3k/files/',
            internalRelativeUrl: '/mst3k/forks/'
        }

        it('Does not affect external URLs', () => {
            assert.equal(logTextParser.toRelativeUrl(testData.externalAbsoluteUrl), testData.externalAbsoluteUrl);
        });

        it('DOes not affect URLs that are already relative', () => {
            assert.equal(logTextParser.toRelativeUrl(testData.internalRelativeUrl), testData.internalRelativeUrl);
        });

        it('Works for internal absolute URLs', () => {
            assert.equal(logTextParser.toRelativeUrl(testData.internalAbsoluteUrl), '/mst3k/files/');
        });
    });
});
