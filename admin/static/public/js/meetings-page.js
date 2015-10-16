webpackJsonp([26],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

var Meetings = __webpack_require__(365);
var Submissions = __webpack_require__(366);

new Meetings(window.contextVars.meetings);
new Submissions(window.contextVars.submissions);


/***/ },

/***/ 365:
/***/ function(module, exports, __webpack_require__) {

var $ = __webpack_require__(38);
var m = __webpack_require__(158);
var Treebeard = __webpack_require__(159);


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
                    title: 'Accepting Submissions',
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


/***/ },

/***/ 366:
/***/ function(module, exports, __webpack_require__) {

var $ = __webpack_require__(38);
var m = __webpack_require__(158);
var osfHelpers = __webpack_require__(47);
var Treebeard = __webpack_require__(159);


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
                    custom : function() {
                        return m('a', { href : item.data.nodeUrl, target : '_blank' }, item.data.title ); }

                },
                {
                    data: 'author',  // Data field name
                    sortInclude: true,
                    custom: function() { return m('a', {href: item.data.authorUrl}, item.data.author); }
                },

                {
                    data: 'dateCreated', // Data field name
                    sortInclude: true,
                    custom: function() {
                        var dateCreated = new osfHelpers.FormattableDate(item.data.dateCreated);
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
                                m('button.btn.btn-success.btn-xs', { style : 'margin-right : 10px;'},  m('i.fa.fa-download.fa-inverse')),

                            ] ), item.data.download  ];
                        } else {
                            return '';
                        }
                    }

                },
                {
                    data: 'confName',
                    sortInclude: true,
                    custom: function() { return m('a', {href: item.data.confUrl}, item.data.confName); }
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

module.exports = Submissions;


/***/ }

});
//# sourceMappingURL=meetings-page.js.map