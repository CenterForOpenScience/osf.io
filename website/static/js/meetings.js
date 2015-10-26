var $ = require('jquery');
var m = require('mithril');
var Treebeard = require('treebeard');


function Meetings(data) {
    //  Treebeard 'All Meetings' Grid
    var tbOptions = {
        divID: 'meetings-grid',
        filesData: data,
        rowHeight : 30,         // user can override or get from .tb-row height
        paginate : false,       // Whether the applet starts with pagination or not.
        paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
        uploads : false,         // Turns dropzone on/off.
        columnTitles : function() {
             return [
                {
                    title: 'Name',
                    width: '50%',
                    sortType : 'text',
                    sort : true
                },
                {
                     title: 'Submissions',
                     width : '25%',
                     sortType : 'number',
                     sort : true
                },
                {
                    title: 'Accepting submissions',
                    width: '25%',
                    sortType: 'text',
                    sort: true
                }
            ];
        },
        resolveRows : function _conferenceResolveRows(item){
            return [
                {
                    data : 'name',  // Data field name
                    sortInclude : true,
                    custom : function() { return m('a', { href : item.data.url, target : '_blank' }, item.data.name ); }

                },
                {
                    data: 'count',
                    sortInclude: true
                },
                {
                    data: 'active', // Data field name
                    sortInclude: true,
                    custom: function() { return item.data.active ? 'Yes' : 'No'; }
                }
            ];
        },
        sortButtonSelector : {
            up : 'i.fa.fa-chevron-up',
            down : 'i.fa.fa-chevron-down'
        },
        hScroll: 'auto',
        showFilter : false,     // Gives the option to filter by showing the filter box.
        allowMove : false,       // Turn moving on or off.
        hoverClass : 'fangorn-hover',
    };

    var grid = new Treebeard(tbOptions);
}

module.exports = Meetings;
