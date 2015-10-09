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
    wrapper : '#fileBrowser',  // Default ID for wrapping empty div, all contents will be filled in.
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
    // Load data

    // Build html
    var wrapper = $(this.options.wrapper);
    if(self.options.views.breadcrumbs){
        this.breadcrumbs = new Breadcrumbs(self.options);
    }
    if(self.options.views.collections){
        this.collections = new Collections(self.options);
    }

};


/**
 * Collections Module.
 * @constructor
 */
function Collections(options) {
    this.wrapper = $(options.wrapper);
    this.init = function () {
        this.wrapper.append('<div>Collections</div>');
    };
    this.init();

}

/**
 * Breadcrumbs Module.
 * @constructor
 */
function Breadcrumbs(options) {
    var self = this;
    this.wrapper = $(options.wrapper);
    this.init = function () {
        console.log(this);
        this.wrapper.append('<div>Breadcrumbs</div>');
    };
}

/**
 * Filters Module.
 * @constructor
 */
function Filters(options) {
    this.wrapper = $(options.wrapper);
    this.init = function () {
        this.wrapper.append('<div>Filters</div>');
    };
    this.init();
}

/**
 * Project Organizer Module.
 * @constructor
 */
function ProjectOrganizer(options) {
    this.wrapper = $(options.wrapper);
    this.init = function () {
        this.wrapper.append('<div>Project Organizer</div>');
    };
    this.init();
}

/**
 * Information Module.
 * @constructor
 */
function Information(options) {
    this.wrapper = $(options.wrapper);
    this.init = function () {
        this.wrapper.append('<div>Information</div>');
    };
    this.init();
}



module.exports = FileBrowser;