/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

var oop = require('js/oop');


describe.skip('oop', () => {
    var constructorSpy = new sinon.spy();
    var methodSpy = new sinon.spy();
    var overrideSpy = new sinon.spy();

    var Thing = oop.defclass({
        constructor: constructorSpy,
        methodA: methodSpy,
        override: function() {
            assert.instanceOf(this, SubThing);
            overrideSpy();
        }
    });

    var suboverrideSpy = new sinon.spy();
    var SubThing = oop.extend(Thing, {
        override: function() {
            this.super.override.call(this);
            suboverrideSpy();
        }
    });

    afterEach(() => {
        constructorSpy.reset();
        methodSpy.reset();
        overrideSpy.reset();
        suboverrideSpy.reset();
    });

    describe('defclass', () => {
        it('returns a constructor', () => {
            new Thing();
            assert.typeOf(Thing, 'function');
            assert.calledOnce(constructorSpy);
        });
    });

    describe('subclasses', () => {
        it('inherit from superclasses', () => {
            var st = new SubThing();
            assert.instanceOf(st, SubThing);
            assert.instanceOf(st, Thing);
        });
        it('inherit methods', () => {
            var st = new SubThing();
            st.methodA();
            assert.calledOnce(methodSpy);
        });
        it('can call super method', () => {
            var st = new SubThing();
            st.override();
            assert.calledOnce(overrideSpy);
            assert.calledOnce(suboverrideSpy);
        });
    });
});
