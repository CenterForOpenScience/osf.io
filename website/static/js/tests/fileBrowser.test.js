/* Tests for fileBrowser.js for My Projects in Dashboard */
/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var fb = require('js/fileBrowser.js');
var m = require('mithril');

var FileBrowser = fb.FileBrowser;
var LinkObject = fb.LinkObject;

describe('fileBrowser', function() {
    describe('LinkObject', function () {
        var collection;
        var tag;
        var name;
        var node;

        before(function () {
            collection = new LinkObject('collection', {
                path: 'users/me/nodes/',
                query: {'related_counts': true},
                systemCollection: true
            }, 'All My Projects');
            tag = new LinkObject('tag', { tag : 'something', query : { 'related_counts' : true }}, 'Something Else');
            name = new LinkObject('name', { id : '8q36f', query : { 'related_counts' : true }}, 'Caner Uguz');
            node = new LinkObject('node', { uid : 'qwerty'}, 'Node Title');
        });

        describe('#attributes', function () {
            it('should return an id of 1', function () {
                assert.equal(collection.id, 1);
            });
            it('should throw error when no arguments passed', function () {
                assert.throws(function(){ var missing = new LinkObject(); }, Error);
            });
            it('should throw error when index is not number and  > 0', function () {
                assert.throws(function(){ var missing = new LinkObject('tag', { tag : 'something', query : { 'related_counts' : true }}, 'Something Else', 'index'); }, Error);
                assert.throws(function(){ var missing = new LinkObject('tag', { tag : 'something', query : { 'related_counts' : true }}, 'Something Else', -1); }, Error);
            });
        });

        describe('#generateLinks', function () {
            it('should return correct collection link', function () {
                assert.equal(collection.link, 'users/me/nodes/?related_counts=true');
            });
            it('should return correct tag link', function () {
                assert.equal(tag.link, 'nodes/?filter%5Btags%5D=something&related_counts=true');
            });
            it('should return correct name link', function () {
                assert.equal(name.link, 'users/8q36f/nodes/?related_counts=true');
            });
            it('should return correct node link', function () {
                assert.equal(node.link, 'nodes/qwerty/children/?related_counts=true');
            });
        });
    });
});