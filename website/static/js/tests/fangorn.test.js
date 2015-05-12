/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';

var assert = require('chai').assert;
var $ = require('jquery');
// var m = require('mithril');
// var URI = require('URIjs');
// var Treebeard = require('treebeard');
//var Fangorn = require('js/fangorn');

//// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
//sinon.assert.expose(assert, {prefix: ''});
//
//var smallSample = [
//	{
//		kind : 'folder',
//		name : 'test folder',
//		provider : 'osf-storage',
//		permissions : {
//			view : true,
//			edit : true
//		},
//		downloads : 0
//	},
//	{
//		kind : 'file',
//		name : 'test file',
//		permissions : {
//			view : true,
//			edit : true
//		},
//		downloads : 1
//	}
//];
//
//var fangornInstance = function() {
//    var fangorn =  new Fangorn({
//        divID: 'fangorn',
//        filesData: smallSample,
//        uploads : false
//    });
//    return fangorn;
//};
//
//describe('fangornToolbars', () => {
//// Tests related to the toolbar
//	  var fangorn;
//	  var tb;
//
//	  before(function() {
//	    // runs before all tests in this block
//	    $('body').append('<div id="fangorn"></div>');
//	    fangorn = fangornInstance();
//	    tb = fangorn.grid.tbController;
//	  });
//	  after(function(){
//	    // runs after all tests in this block
//	    $('#fangorn').remove();
//	    fangorn.grid.tbController.destroy();
//	  });
//
//	describe('fangornToolbar', () => {
//	  it('should return bar view when state is changed to bar', function() {
//	  	tb.options.iconState.mode = 'bar';
//	  	var template = fangorn.tests.fangornToolbar.call(tb);
//	  	assert.equal(template.attrs['data-mode'], 'bar');
//	  });
//	  it('Should return search view when state is changed to search', function() {
//	  	tb.options.iconState.mode = 'bar';
//	  	var template = fangorn.tests.fangornToolbar.call(tb);
//	  	assert.equal(template.attrs['data-mode'], 'bar');
//	  });
//	});
//
//	describe('toolbarStateChanges', () => {
//		it('Should build item buttons for file', function() {
//			// 2 and 1 are the assigned ID's to the raw data above, this will always be the case in this test scenario.
//			var fileItem = tb.find(2);
//			fangorn.tests.defineToolbar.call(tb, fileItem);
//			assert.equal(fileItem.icons.length, 2);
//		 });
//		it('Should build item buttons for folder', function() {
//			// 2 and 1 are the assigned ID's to the raw data above, this will always be the case in this test scenario.
//			var folderItem = tb.find(1);
//			fangorn.tests.defineToolbar.call(tb, folderItem);
//			assert.equal(folderItem.icons.length, 1);
//		 });
//
//	});
//
//});
//