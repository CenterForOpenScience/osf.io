/**
 * Builds full page project browser
 */
'use strict';

var Treebeard = require('treebeard');   // Uses treebeard, installed as plugin
var $ = require('jquery');  // jQuery
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.


/**
 *  Options for fileBrowser
 */
var defaults = {
    tboptions : {},
    fullWidth : true,
    views : {
        collections : true,
        filters : true,
        browser : true,
        info : true,
        breadcrumbs : true,
    }
};

/**
 * Initialize File Browser. Prepeares an option object within FileBrowser
 * @constructor
 */
function FileBrowser(options) {
    this.options = $.extend({}, defaults, options);
    this.init();
}

FileBrowser.prototype.init = function _fb_init () {
    var self = this;
    console.log(self);
};

module.exports = FileBrowser;