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
var FileBrowser = {
    controller : function (args) {
        this.args = $.extend({}, defaults, args);
    },
    view : function (ctrl) {
        return m('', [
            m.component(Breadcrumbs),
            m('.fb-sidebar', [
                m.component(Collections),
                m.component(Filters)
            ]),
            m('.fb-main', m.component(ProjectOrganizer)),
            m('.fb-infobar', m.component(Information))
        ]);
    }
};

/**
 * Collections Module.
 * @constructor
 */
var Collections  = {
    controller : function (args) {

    },
    view : function (ctrl) {
        return m('.fb-collections', 'Collections');
    }
};

/**
 * Breadcrumbs Module.
 * @constructor
 */
var Breadcrumbs = {
    controller : function (args) {

    },
    view : function (ctrl) {
        return m('.fb-breadcrumbs', 'Breadcrumbs');
    }
};


/**
 * Filters Module.
 * @constructor
 */
var Filters = {
    controller : function (args) {

    },
    view : function (ctrl) {
        return m('.fb-filters', 'Filters');
    }
};


/**
 * Project Organizer Module.
 * @constructor
 */
var ProjectOrganizer = {
    controller : function (args) {

    },
    view : function (ctrl) {
        return m('.fb-project-organizer', 'Project Organizer');
    }
};


/**
 * Information Module.
 * @constructor
 */
var Information = {
    controller : function (args) {

    },
    view : function (ctrl) {
        return m('.fb-information', 'Information');
    }
};



module.exports = FileBrowser;