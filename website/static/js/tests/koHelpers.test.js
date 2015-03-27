/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var ko = require('knockout');

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

    describe('mapJStoKO', () => {
        var parent;
        var data;

        before(() => {
            parent = {
                comment: "Not great.",
                overarching: ko.observable(10),
                indesc: ko.observable(42)
            };
            data = {
                thursday: "Before Friday",
                object2: {
                    offer: "Greatly appreciated",
                    other: 5
                },
                array2: [5, 4, 3, 2, 1],
                more: "The other day",
                number: 243
            };
            koHelpers.mapJStoKO(data, parent);
        });

        it('makes observables', () => {
            assert.isTrue(ko.isObservable(parent.thursday));
            assert.isTrue(ko.isObservable(parent.more));
            assert.isTrue(ko.isObservable(parent.number));
            assert.isTrue(parent.hasOwnProperty("object2"));
            assert.isTrue(parent.hasOwnProperty("array2"));
        });

        //Remove when arrayMap and deep is added.
        it('arrays and objects are not observables', () => {
            assert.isFalse(ko.isObservable(parent.object2));
            assert.isFalse(ko.isObservable(parent.array2));
        });
    });
});
