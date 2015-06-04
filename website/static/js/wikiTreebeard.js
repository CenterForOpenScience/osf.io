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
        rowHeight: 33,
        resolveToggle: resolveToggle,
        paginate : false,       // Whether the applet starts with pagination or not.
        paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
        uploads : false,         // Turns dropzone on/off.
        hideColumnTitles: true,
        resolveIcon : resolveIcon,
        ontogglefolder : function (item){
            var containerHeight = this.select('#tb-tbody').height();
            this.options.showTotal = Math.floor(containerHeight / this.options.rowHeight) + 1;
            this.redraw();
        },
        resolveRows : function (item){
            var columns = [];
            var iconcss = '';
            // check if should not get icon
            if(item.children.length < 1 ){
                iconcss = 'tb-no-icon';
            }

            if(item.data.kind === 'project') {
                columns.push({
                    data: 'project',
                    folderIcons: false,
                    custom: function() {
                        if(item.data.page.title == 'home') {
                           return m('a', {href: item.data.page.url}, 'Home');
                        }
                        return m('a', {href: item.data.page.url}, item.data.page.title);
                    }
                });
            } else {
                columns.push({
                    data: 'project',
                    folderIcons: true,
                    custom: function() {
                        return m('a', {href: item.data.page.url}, item.data.page.title);
                    }
                });
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
