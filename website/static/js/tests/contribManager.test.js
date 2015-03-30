/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $osf = require('js/osfHelpers');

var contribManager = require('js/contribManager');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('contribManager', () => {
    describe('ViewModels', () => {

        describe('ContributorsViewModel', () => {
            var vm;

            beforeEach(() => {
                //vm = new contribManager.ContributorsViewModel();
            });

            it('valid is valid', () => {
                assert.isTrue(true);
            });
        });
    });
});