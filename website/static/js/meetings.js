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
                    width: '45%',
                    sortType : 'text',
                    sort : true
                },
                {
                    title: 'Submissions',
                    width : '15%',
                    sortType : 'number',
                    sort : true
                },
                {
                    title: 'Location',
                    width : '20%',
                    sortType : 'text',
                    sort : true
                },
                {
                    title: 'Date',
                    width: '20%',
                    sortType: 'date',
                    sort: true
                }
            ];
        },
        resolveRows : function _conferenceResolveRows(item){
            return [
                {
                    data : 'name',  // Data field name
                    sortInclude : true,
                    filter : true,
                    custom : function() { return m('a', { href : item.data.url, target : '_blank' }, item.data.name ); }

                },
                {
                    data: 'count',
                    sortInclude: true,
                    custom: function(){
                        return m('span.text-center', item.data.count );
                    }
                },
                {
                    data: 'location',
                    sortInclude : true,
                    custom : function() {
                        return item.data.location; }
                },
                {
                    data: 'start_date', // Data field name
                    sortInclude : true,
                    custom: function() {
                        if (item.data.start_date === null && item.data.end_date === null){
                            return;
                        }
                        if (item.data.start_date === null) {
                            return item.data.end_date;
                        }
                        if (item.data.end_date === null) {
                            return item.data.start_date;
                        }
                        if (item.data.end_date === item.data.start_date) {
                            return item.data.end_date;
                        }
                        return item.data.start_date + ' - ' + item.data.end_date;
                    },
                    filter : false
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

module.exports = Meetings;
