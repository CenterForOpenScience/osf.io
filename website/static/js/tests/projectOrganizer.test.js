/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var moment = require('moment');
var Raven = require('raven-js');

var ProjectOrganizer = require('projectOrganizer');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('ProjectOrganizer', () => {
    var parent = {
        name: 'Parent',
        isAncestor: function() {
            return true;
        }
    };

    var child = {
        name: 'Child',
        isAncestor: function() {
            return false;
        }
    };

    describe('whichIsContainer', () => {
        it('says children are contained in parents', () => {
            var ancestor = ProjectOrganizer._whichIsContainer(parent, child);
            assert.equal(ancestor.name, 'Parent');
        });

        it('says parents contain children', () => {
             var ancestor = ProjectOrganizer._whichIsContainer(child, parent);
            assert.equal(ancestor.name, 'Parent');
        });
        it('says nothing if both contain each other', () => {
             var ancestor = ProjectOrganizer._whichIsContainer(parent, parent);
            assert.equal(ancestor, null);
        });
        it('says nothing if neither contains the other', () => {
            var ancestor = ProjectOrganizer._whichIsContainer(child, child);
            assert.equal(ancestor, null);
        });
    });
});