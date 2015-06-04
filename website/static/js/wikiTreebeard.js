'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
var m = require('mithril');
var Treebeard = require('treebeard');
var $osf = require('js/osfHelpers');
require('../css/fangorn.css');


function resolveToggle(item) {
    var toggleMinus = m('i.fa.fa-minus', ' '),
        togglePlus = m('i.fa.fa-plus', ' ');

    if (item.children.length > 0) {
        if (item.open) {
            return toggleMinus;
        }
        return togglePlus;
    }
    item.open = true;
    return '';
}

function resolveIcon(item) {
    if (item.children.length > 0) {
        if (item.open) {
            return m('i.fa.fa-folder-open', ' ');
        }
        return m('i.fa.fa-folder', ' ');
    }
}


function WikiMenu(data) {

    //  Treebeard version
    var tbOptions = {
        divID: 'grid',
        filesData: data,
        resolveToggle: resolveToggle,
        paginate : false,       // Whether the applet starts with pagination or not.
        paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
        uploads : false,         // Turns dropzone on/off.
        hideColumnTitles: true,
        resolveIcon : resolveIcon,
        columnTitles: function () {
            return[{
                title: 'Name',
                width: '100%'
            }]
        },
        resolveRows : function (item){

            var columns = [];

            if(item.data.kind === 'heading') {
                columns.push(
                    {
                        folderIcons: true,
                        custom: function() {
                            return m('b', item.data.title);
                        }
                    }
                )
            } else {
                columns.push(
                    {
                        folderIcons: true,
                        custom: function() {
                            return m('a', {href: item.data.page.url}, item.data.page.name);
                        }
                    }
                )
            }

            return columns;
        },
        showFilter : false,     // Gives the option to filter by showing the filter box.
        allowMove : false,       // Turn moving on or off.
        hoverClass : 'fangorn-hover',
        resolveRefreshIcon : function() {
          return m('i.fa.fa-refresh.fa-spin');
        }
    };
    var grid = new Treebeard(tbOptions);
}

module.exports = WikiMenu;
