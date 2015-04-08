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

var fangornInstance = function() {
    var fan =  new Fangorn({
        divID: 'fangorn',
        filesData: smallSample
    });
    return fan.grid.tbController;
};

describe('fangornToolbars', () => {
// Tests related to the toolbar
	describe('toolbarOptions', () => {
	  var fangorn; 
	  beforeEach(function() {
	    // runs before all tests in this block
	    $('body').append('<div id="fangorn"></div>');
	    fangorn = fangornInstance();
	  });
	  afterEach(function(){
	    // runs after all tests in this block
	    $('#fangorn').remove();
	  });

	  it('Should have fangorn toolbar template', function() {
	  	assert.ok(fangorn.options.headerTemplate);
	  });
	  it('fangorn toolbar template should returns an object', function() {
	  	var template = fangorn.options.headerTemplate.call(fangorn);
	  	assert.equal(typeof template, 'object');
	  });



	});

});
  