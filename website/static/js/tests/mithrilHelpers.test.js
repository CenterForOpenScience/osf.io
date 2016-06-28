/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var m = require('mithril');
var mHelpers = require('../mithrilHelpers');

describe('mithrilHelpers', () => {
    describe('unwrap', () => {
        it('unwraps prop', () => {
            var prop = m.prop('Value');
            var propValue = mHelpers.unwrap(prop);
            assert.equal(propValue, 'Value');
        });
        it('unwraps value', () => {
            var prop = 'Value';
            var propValue = mHelpers.unwrap(prop);
            assert.equal(propValue, 'Value');
        });
    });
});
