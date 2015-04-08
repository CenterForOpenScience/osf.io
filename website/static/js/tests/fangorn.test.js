/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';

var assert = require('chai').assert;
var $ = require('jquery');
var m = require('mithril');
var URI = require('URIjs');
var Treebeard = require('treebeard');
var Fangorn = require('js/fangorn');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

var smallSample = [ {kind : 'folder', name : 'test folder'}, { kind : 'file', name : 'test file'}];

describe('fangornToolbars', () => {
// Tests related to the toolbar
	describe('toolbarOptions', () => {
	// header template is defined 


	});

});
