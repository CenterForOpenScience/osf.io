/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';


var oop = require('js/oop');
var assert = require('chai').assert;
var ChangeMessageMixin = require('js/changeMessage');
sinon.assert.expose(assert, {prefix: ''});


describe('ChangeMessageMixin', () => {
    var vm;
    var message;
    var messageClass;

    beforeEach(() => {
        vm = new ChangeMessageMixin();
    });

    afterEach(() => {
        message = '';
        messageClass = 'text-info';
    });

    it('changeMessage', () => {
        message = 'Invalid';
        messageClass = 'text-danger';
        vm.changeMessage(message, messageClass);
        assert.equal(vm.message(), message);
        assert.equal(vm.messageClass(), messageClass);
    });

    var timer;
    before(() => {
        timer = sinon.useFakeTimers();
    });
    after(() => {
        timer.restore();
    });
    it('message is removed after a timeout if supplied', () => {
        message = 'Invalid';
        messageClass = 'text-danger';
        var oldMsg = vm.message();
        var oldCls = vm.messageClass();
        vm.changeMessage(message, messageClass, 100);
        timer.tick(105);
        assert.equal(vm.message(), oldMsg);
        assert.equal(vm.messageClass(), oldCls);
    });
});
