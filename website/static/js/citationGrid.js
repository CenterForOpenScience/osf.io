'use strict';

var $ = require('jquery');
var m = require('mithril');
var Treebeard = require('treebeard');
var citations = require('./citations');
require('../vendor/bower_components/treebeard/dist/treebeard.css');
require('../css/fangorn.css');
var style = require('raw!styles/apa.csl');


/**
 * Returns custom folder toggle icons for OSF
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {string} Returns a mithril template with m() function, or empty string.
 * @private
 */
function resolveToggle(item) {
    var toggleMinus = m('i.icon-minus', ' '),
        togglePlus = m('i.icon-plus', ' ');
    // check if folder has children whether it's lazyloaded or not.
    if (item.kind === 'folder') {
        if (item.open) {
            return toggleMinus;
        }
        return togglePlus;
    }
    return '';
}

/**
 * Returns custom icons for OSF depending on the type of item
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {Object}  Returns a mithril template with the m() function.
 * @private
 */
function resolveIcon(item) {
    var privateFolder = m('img', {
            src: '/static/img/hgrid/fatcowicons/folder_delete.png'
        }),
        pointerFolder = m('i.icon-link', ' '),
        openFolder = m('i.icon-folder-open', ' '),
        closedFolder = m('i.icon-folder-close', ' '),
        configOption = item.data.provider ? resolveconfigOption.call(this, item, 'folderIcon', [item]) : undefined,
        ext,
        extensions;

    if (item.kind === 'folder') {
        if (item.open) {
            return configOption || openFolder;
        }
        return configOption || closedFolder;
    }
    if (item.data.icon) {
        return m('i.fa.' + item.data.icon, ' ');
    }

    return m('i.icon-file-alt');
}


var utils = {
    reduce: function(array, dst, fn) {
        for (var i = 0; i < array.length; i++) {
            fn(array[i], dst);
        }
        return dst;
    },
    zip: function(array1, array2) {
        var zipped = [];
        var min = Math.min(array1.length, array2.length);
        for (var i = 0; i < min; i++) {
            zipped.push([array1[i], array2[i]]);
        }
        return zipped;
    }
};

var getColumns = function() {
    return [{
        title: 'Citation',
        sort: false
    }];
};

var getRowCallback = function(item) {

};

var getRow = function(item) {
    return [{
        data: 'csl',
        custom: function(item) {
            if (item.kind === 'folder') {
                return 'FOLDER';
            }
            return item.data.citation;
        },
        folderIcons: true
    }];
};
var citationsApiUrl = window.contextVars.node.urls.api + 'mendeley/citations/';
var parent = {
    kind: 'folder',
    urls: {
        fetch: citationsApiUrl
    },
    children: []
};
var citeproc;

var CitationGrid = function(selector, url) {

        var options = {
            divID: selector.replace('#', ''),
            columnTitles: getColumns,
            resolveRows: getRow,
            // filesData: citationsApiUrl,
            filesData: [parent],
            resolveLazyloadUrl: function(item) {
                return item.data.urls.fetch;
            },
            lazyLoad: true,
            lazyloadPreprocess: function(data) {
		var citationObj = utils.reduce(
                    data.map(
			function(item) {
                            return item.csl;
                       }
                   ), {},
                   function(item, dst) {
                       dst[item.id] = item;
                    });
                citeproc = citations.makeCiteproc(style, citationObj, 'text');
                var bibliography = citeproc.makeBibliography();
                var combinedData = utils.reduce(
                    utils.zip(bibliography[0].entry_ids, bibliography[1]), {},
                    function(tup, dst) {
                        return dst[tup[0][0]] = tup[1]
                    }
                );
		data = data.map(function(item){
		    item.citation = combinedData[item.csl.id];
		    return item;
		});
		return data;
            },
	    resolveIcon: resolveIcon,
	    resolveToggle: resolveToggle
	};
    
    var treebeard = new Treebeard(options);
};

module.exports = CitationGrid;
