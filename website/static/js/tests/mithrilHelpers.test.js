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

    describe.only('apiV2Config', () => {
        it('can be called with no arguments', () => {
            var func = mHelpers.apiV2Config();
            assert.isFunction(func);
            var mockXHR = {
                setRequestHeader: function() {}
            };
            assert.doesNotThrow(func.bind(this, mockXHR), Error);
        });

        it('sets withCredentials to true by default', () => {
            var func = mHelpers.apiV2Config();
            var mockXHR = {
                setRequestHeader: function() {}
            };
            func(mockXHR);
            assert.isTrue(mockXHR.withCredentials);
        });

        it('can set withCredentials to false', () => {
            var func = mHelpers.apiV2Config({withCredentials: false});
            var mockXHR = {
                setRequestHeader: function() {}
            };
            func(mockXHR);
            assert.isFalse(mockXHR.withCredentials);
        });
    });
});
