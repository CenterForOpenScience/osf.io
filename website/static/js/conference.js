var $ = require('jquery');
var m = require('mithril');
var Treebeard = require('treebeard');


function Meeting(data) {
    //  Treebeard version
    var tbOptions = {
        divID: 'grid',
        filesData: data,
        rowHeight : 30,         // user can override or get from .tb-row height
        paginate : false,       // Whether the applet starts with pagination or not.
        paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
        uploads : false,         // Turns dropzone on/off.
        columnTitles : function _conferenceColumnTitles(item, col) {
             return [
                {
                    title: 'Title',
                    width: '50%',
                    sortType : 'text',
                    sort : true
                },
                {
                    title: 'Author',
                    width : '20%',
                    sortType : 'text',
                    sort : true
                },
                {
                    title: 'Category',
                    width : '15%',
                    sortType : 'text',
                    sort : true
                },
                {
                    title: 'Downloads',
                    width : '15%',
                    sortType : 'number',
                    sort : true
                }
            ];
        },
        resolveRows : function _conferenceResolveRows(item){
            var default_columns = [
                {
                    data : 'title',  // Data field name
                    folderIcons : false,
                    filter : true,
                    sortInclude : true,
                    custom : function() { return m('a', { href : item.data.nodeUrl, target : '_blank' }, item.data.title ); }

                },
                {
                    data : 'author',  // Data field name
                    folderIcons : false,
                    filter : true,
                    sortInclude : true,
                    custom : function() { return m('a', { href : item.data.authorUrl }, item.data.author ); }
                },
                {
                    data : 'category',  // Data field name
                    folderIcons : false,
                    filter : false
                },
                {
                    data : 'download',  // Data field name
                    folderIcons : false,
                    filter : false,
                    custom : function() {
                        if(item.data.downloadUrl){
                            return [ m('a', { href : item.data.downloadUrl }, [
                                m('button.btn.btn-success.btn-xs', { style : 'margin-right : 10px;'},  m('i.fa.fa-download.fa-inverse')),

                            ] ), item.data.download  ];
                        } else {
                            return '';
                        }
                    }

                }
            ];
            return default_columns;
        },
        sortButtonSelector : {
            up : 'i.fa.fa-chevron-up',
            down : 'i.fa.fa-chevron-down'
        },
        showFilter : true,     // Gives the option to filter by showing the filter box.
        filterStyle : { 'float' : 'right', 'width' : '50%'},
        allowMove : false,       // Turn moving on or off.
        hoverClass : 'fangorn-hover'
    };
    var grid = new Treebeard(tbOptions);
}

module.exports = Meeting;
