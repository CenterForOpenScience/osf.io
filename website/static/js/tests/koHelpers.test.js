/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var koHelpers = require('../koHelpers');
// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('koHelpers', () => {
    describe('sanitizedObservable', () => {
        it('removes html', () => {
            var obs = koHelpers.sanitizedObservable();
            ['foo', '<b>foo</b>', '<b>foo'].forEach((input) => {
                obs(input);
                assert.equal(obs(), 'foo', input + ' is sanitized correctly');
            });
        });
    });

    // TODO: test custom validators
});
