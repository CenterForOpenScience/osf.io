/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var ko = require('knockout');

var koHelpers = require('../knockoutPassword');
// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('the passwordChecking extender', () => {
    var obs;
    beforeEach(() => {
        obs = ko.observable().extend({passwordChecking: true});
    });
    it('should measure password complexity', () => {
        obs('');
        assert.equal(obs.passwordComplexity(), 0);

        obs('supersecurepassword123456');
        assert.isNumber(obs.passwordComplexity());

        obs('password');

        var weakComplexity = obs.passwordComplexity();

        obs('Pb6ePPPb7FcBgCKEDDbuuapAKYzVqy');

        var strongComplexity = obs.passwordComplexity();

        assert.isTrue(strongComplexity > weakComplexity);

    });

    it('should have password feedback', () => {
        obs('');
        assert.deepEqual(obs.passwordFeedback(), {});

        obs('password');
        assert.isObject(obs.passwordFeedback());
        assert.equal(obs.passwordFeedback().warning, 'This is a top-10 common password');
    });
});
