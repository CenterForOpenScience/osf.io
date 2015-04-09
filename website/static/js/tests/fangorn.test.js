/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';

var assert = require('chai').assert;
var $ = require('jquery');
// var m = require('mithril');
// var URI = require('URIjs');
// var Treebeard = require('treebeard');
var Fangorn = require('js/fangorn');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

var smallSample = [
	{ 
		kind : 'folder', 
		name : 'test folder',
		permissions : {
			view : true,
			edit : true
		},
		downloads : 0
	}, 
	{ 
		kind : 'file', 
		name : 'test file',
		permissions : {
			view : true,
			edit : true
		},
		downloads : 1
	}
];

var fangornInstance = function() {
    var fangorn =  new Fangorn({
        divID: 'fangorn',
        filesData: smallSample,
        uploads : false
    });
    return fangorn;
};

describe('fangornToolbars', () => {
// Tests related to the toolbar
	  var fangorn; 

	  before(function() {
	    // runs before all tests in this block
	    $('body').append('<div id="fangorn"></div>');
	    fangorn = fangornInstance();
	  });
	  after(function(){
	    // runs after all tests in this block
	    $('#fangorn').remove();
	    fangorn.grid.tbController.destroy();
	  });

	describe('toolbarOptions', () => {
	  it('Should have fangorn toolbar template', function() {
	  	assert.ok(fangorn.grid.tbController.options.headerTemplate);
	  });
	  it('Should return an object for fangorn toolbar template', function() {
	  	var template = fangorn.tests.fangornToolbar.call(fangorn.grid.tbController);
	  	assert.equal(typeof template, 'object');
	  });
	});

	describe('toolbarStateChanges', () => {
		it('Should build item buttons', function() {
			var fileItem = fangorn.grid.tbController.find(2);
			fangorn.tests.defineToolbar.call(fangorn.grid.tbController, fileItem);
			assert.equal(fileItem.icons.length, 2);
		 });

	});

});
  