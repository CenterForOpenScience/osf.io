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
        var self = this;
        self.args = $.extend({}, defaults, args);
        self.data = m.prop([]);
        m.request({method: "GET", url: args.url}).then(self.data).then(function(){ console.log(self.data())});
        self.path = [
            { label : 'First', href : "/first"},
            { label : 'Second', href : "/second"},
            { label : 'Third', href : "/third"},
        ];
    },
    view : function (ctrl) {
        return m('', [
            m.component(Breadcrumbs, ctrl.path),
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
    controller : function (data) {
        this.data = data || [];
    },
    view : function (ctrl) {
        return m('.fb-breadcrumbs', m('ul', [
            ctrl.data.map(function(item, index, array){
                if(index === array.length-1){
                    return m('li',  item.label);
                }
                return m('li',
                    m('a', { href : item.href},  item.label),
                    m('i.fa.fa-chevron-right')
                );
            })
        ]));
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