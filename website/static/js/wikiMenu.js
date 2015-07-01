'use strict';
var m = require('mithril');
var iconmap = require('js/iconmap');
var Treebeard = require('treebeard');
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
    var componentIcons = iconmap.componentIcons;
    function returnView(category) {
        var iconType = componentIcons[category];
        return m('span', { 'class' : iconType});
    }
    if (item.data.kind === 'component' && item.parent().data.title === 'Component Wiki Pages') {
        return returnView(item.data.category);
    }
    if (item.data.type === 'heading' && item.data.children.length > 0 ) {
        if (item.open) {
            return m('i.fa.fa-folder-open', ' ');
        }
        return m('i.fa.fa-folder', ' ');
    }
    return m('i.fa.fa-file-o', ' ');
}

var WikiMenuToolbar = {
    controller : function(args) {
        var self = this;
        self.tb = args.treebeard;
        self.items = self.tb.multiselected;
    },
    view : function(ctrl) {
        var items = ctrl.items();
        var item = items[0];
        var buttons = [];
        if(item) {
            if(window.contextVars.wiki.canEdit) {
                buttons.push(
                    m('a.fangorn-toolbar-icon.text-success', {'data-toggle': 'modal', 'data-target': '#newWiki'}, [
                        m('i.fa.fa-plus.text-success'),
                        m('span', 'New')
                    ])
                );
                if(item.data.page.name !== 'home') {
                    buttons.push(
                        m('a.fangorn-toolbar-icon.text-danger', {'data-toggle': 'modal', 'data-target': '#deleteWiki'}, [
                            m('i.fa.fa-trash-o.text-danger'),
                            m('span', 'Delete')
                        ])
                    )
                }
            } else {
                buttons.push(
                    m('', [m('i.fa.fa-list')], 'Menu')
                );
            }
        }
        return m('.row.tb-header-row', [
            m('#toolbarRow', [
                m('.col-xs-12', [buttons])
            ])
        ]);
    }
};

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
        resolveToggle : resolveToggle,
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
                if(item.data.children.length >  0) {
                    columns.push({
                        folderIcons: true,
                        custom: function() {
                            return m('b', item.data.title);
                        }
                    });
                }
            } else {
                if(item.data.page.id === wikiID) {
                    item.css = 'fangorn-selected';
                    tb.multiselected([item]);
                }
                columns.push({
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
                        if(item.data.kind === 'component') {
                            return m('a', {href: item.data.page.url}, item.data.page.name, [
                                m('i.fa.fa-external-link.tb-td-first')
                            ]);
                        } else {
                            return m('a', {href: item.data.page.url}, item.data.page.name);
                        }
                    }
                });
            }
            return columns;
        },
        hScroll: 500,
        toolbarComponent: WikiMenuToolbar,
        showFilter : false,     // Gives the option to filter by showing the filter box.
        allowMove : false,       // Turn moving on or off.
        hoverClass : 'fangorn-hover',
        resolveRefreshIcon : function() {
            return m('i.fa.fa-refresh.fa-spin');
        }
    };
    var grid = new Treebeard(tbOptions);
}

WikiMenu.Components = {
    toolbar : WikiMenuToolbar
};

module.exports = WikiMenu;
