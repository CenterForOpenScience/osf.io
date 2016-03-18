var $ = require('jquery');
var m = require('mithril');
var osfHelpers = require('js/osfHelpers');
var Treebeard = require('treebeard');


function Submissions(data) {
    //  Treebeard 'All Submissions' Grid
    var tbOptions = {
        divID: 'submissions-grid',
        filesData: data,
        rowHeight : 30,         // user can override or get from .tb-row height
        paginate : false,       // Whether the applet starts with pagination or not.
        paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
        uploads : false,         // Turns dropzone on/off.
        columnTitles : function() {
             return [
                {
                    title: 'Title',
                    width: '30%',
                    sortType : 'text',
                    sort : true
                },
                {
                     title: 'Author',
                     width : '15%',
                     sortType : 'text',
                     sort : true
                },
                {
                    title: 'Date Created',
                    width: '15%',
                    sortType: 'date',
                    sort: true
                },
                {
                    title: 'Downloads',
                    width: '15%',
                    sortType: 'number',
                    sort: true
                },
                {
                    title: 'Conference',
                    width: '25%',
                    sortType: 'text',
                    sort: true
                }
            ];
        },
        resolveRows : function _conferenceResolveRows(item) {
            return [
                {
                    data : 'title',  // Data field name
                    sortInclude : true,
                    filter : true,
                    custom : function() {
                        return m('a', { href : item.data.nodeUrl, target : '_blank' }, item.data.title ); }

                },
                {
                    data: 'author',  // Data field name
                    sortInclude: true,
                    custom: function() { return m('a', {href: item.data.authorUrl, target : '_blank'}, item.data.author); },
                    filter : true
                },
                {
                    data: 'dateCreated', // Data field name
                    sortInclude: true,
                    filter : false,
                    custom: function() {
                        var dateCreated = new osfHelpers.FormattableDate(item.data.dateCreated);
                        // Assign dateCreated with the format of date usable in all browsers
                        item.data.dateCreated = dateCreated.date;
                        return m('', dateCreated.local);
                    }
                },
                {
                    data : 'download',  // Data field name
                    folderIcons : false,
                    filter : false,
                    custom : function() {
                        if(item.data.downloadUrl){
                            return [ m('a', { href : item.data.downloadUrl }, [
                                m('button.btn.btn-success.btn-xs', { style : 'margin-right : 10px;'},  m('i.fa.fa-download.fa-inverse'))

                            ] ), item.data.download  ];
                        } else {
                            return '';
                        }
                    }

                },
                {
                    data: 'confName',
                    sortInclude: true,
                    filter : true,
                    custom: function() { return m('a', {href: item.data.confUrl, target : '_blank'}, item.data.confName); }
                }
            ];
        },
        sortButtonSelector : {
            up : 'i.fa.fa-chevron-up',
            down : 'i.fa.fa-chevron-down'
        },
        hScroll: 'auto',
        showFilter : true,     // Gives the option to filter by showing the filter box.
        allowMove : false,       // Turn moving on or off.
        hoverClass : 'fangorn-hover',
    };

    var grid = new Treebeard(tbOptions);
}

module.exports = Submissions;
