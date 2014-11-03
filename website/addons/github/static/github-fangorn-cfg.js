/**
 * Github FileBrowser configuration module.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['js/fangorn'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('fangorn', function() { factory(Fangorn); });
    } else { factory(Fangorn); }
}(this, function(Fangorn) {

    // Define Fangorn Button Actions
    function _fangornActionColumn (item, col){
        var self = this;
        var buttons = [];

        // Download Zip File
        if (item.kind === 'folder') {
            buttons.push({
                'name' : '',
                'icon' : 'item.data.urls.',
                'css' : 'fangorn-clickable btn btn-default btn-xs',
                'onclick' : function(){window.location = item.data.urls.zip;}
            });
        }

        //Download button if this is an item
        if (item.kind === 'item') {
            buttons.push({
                'name' : '',
                'icon' : 'icon-download-alt',
                'css' : 'btn btn-info btn-xs',
                'onclick' : function(){window.location = item.data.urls.repo;}//GO TO EXTERNAL PAGE
            }
            );
        }
    }

     var _fangornColumns = [
        {
            title: 'Name',
            width : '60%',
            data : 'name',
            sort : true,
            sortType : 'text',
            filter : true,
            folderIcons : true
        },
        {
            title : 'Actions',
            width : '20%',
            sort : false,
            filter : false,
            css : 'action-col',
            custom : _fangornActionColumn
        },
        {
            title : 'Downloads',
            width : '20%',
            data  : 'downloads',
            sort : false,
            filter : false,
            css : ''
        }
    ];

    // Register configuration
    Fangorn.cfg.github = {
        // Handle changing the branch select
        column:_fangornColumns
        /*listeners: [{
            on: 'change',
            selector: '.github-branch-select',
            callback: function(evt, row, grid) {
                //var $this = $(evt.target);
                //var branch = $this.val();
                Treebeard.redraw();
            }
        }]*/
    };
}));
