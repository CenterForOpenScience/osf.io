/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $osf = require('js/osfHelpers');

var ChangeMessageMixin = require('js/changeMessage');

describe('ChangeMessageMixin', () => {
    var changeable = new ChangeMessageMixin();
    describe('#resetMessage', () => {
        it('sets the View Model\'s message to an empty string and sets the messageClass to "text-info"', () => {
            changeable.message('Some message');
            changeable.messageClass('some-class');
            changeable.resetMessage();
            assert.equal(changeable.message(), '');
            assert.equal(changeable.messageClass(), 'text-info');
        });
    });
    describe('#changeMessage', () => {
        it('updates the VM\'s message and message CSS class', () => {
            changeable.resetMessage();
            var msg = 'Such success!';
            var cls = 'text-success';
            changeable.changeMessage(msg, cls);
            assert.equal(changeable.message(), msg);
            assert.equal(changeable.messageClass(), cls);
            msg = 'Much fail!';
            cls = 'text-error';
            changeable.changeMessage(msg, cls);
            assert.equal(changeable.message(), msg);
            assert.equal(changeable.messageClass(), cls);
        });
        var timer;
        before(() => {
            timer = sinon.useFakeTimers();
        });
        after(() => {
            timer.restore();
        });
        it('... and removes the message after a timeout if supplied', () => {
            changeable.resetMessage();
            var oldMsg = changeable.message();
            var oldCls = changeable.messageClass();
            var msg = 'Such success!';
            var cls = 'text-success';
            changeable.changeMessage(msg, cls, 200);
            timer.tick(201);
            assert.equal(changeable.message(), oldMsg);
            assert.equal(changeable.messageClass(), oldCls);
        });
    });
});
