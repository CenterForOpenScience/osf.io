'use strict';
var m = require('mithril');
var Treebeard = require('treebeard');
require('../css/fangorn.css');

function resolveIcon(item) {
    if (item.children.length > 0) {
        if (item.open) {
            return m('i.fa.fa-folder-open-o', ' ');
        }
        return m('i.fa.fa-folder-o', ' ');
    }
}

function WikiMenu(data, wikiID, canEdit) {

    //  Treebeard version
    var tbOptions = {
        divID: 'grid',
        filesData: data,
        paginate : false,       // Whether the applet starts with pagination or not.
        paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
        uploads : false,         // Turns dropzone on/off.
        hideColumnTitles: true,
        resolveIcon : resolveIcon,
        columnTitles: function () {
            return[{
                title: 'Name',
                width: '100%'
            }];
        },
        onload: function() {
            var tb = this;  // jshint ignore: line
            for (var i = 0; i < tb.treeData.children.length; i++) {
                var parent = tb.treeData.children[i];
                if (parent.data.title === 'Project Wiki Pages') {
                    tb.updateFolder(null, parent);
                }
            }
        },
        resolveRows : function (item){
            var tb = this;
            var columns = [];
            if(item.data.type === 'heading') {
                columns.push(
                    {
                        folderIcons: true,
                        custom: function() {
                            return m('b', item.data.title);
                        }
                    }
                );
            } else {
                if(item.data.page.id === wikiID) {
                    item.css = 'fangorn-selected';
                    tb.multiselected([item]);
                }
                columns.push(
                    {
                        folderIcons: true,
                        custom: function() {
                            if(item.data.page.name === 'home') {
                                return m('a', {href: item.data.page.url}, 'Home');
                            }
                            if(item.data.page.wiki_content === '' && !canEdit) {
                                return [
                                    m('h', item.data.page.name),
                                    m('span',
                                        [m('i', {class: 'text-muted', style: 'padding-left: 10px'}, 'No wiki content')]
                                    )
                                ];
                            }
                            return m('a', {href: item.data.page.url}, item.data.page.name);
                        }
                    }
                );
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
