/**
 * Dataverse FileBrowser configuration module.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['js/rubeus'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('rubeus', function() { factory(Rubeus); });
    } else { factory(Rubeus); }
}(this, function(Rubeus) {

    // Private members
    function refreshDataverseTree(grid, item, state) {
        var data = item.data || {};
        data.state = state;
        var url = item.urls.state + '?' + $.param({state: state});
        $.ajax({
            type: 'get',
            url: url,
            success: function(data) {
                // Update the item with the new state data
                $.extend(item, data[0]);
                grid.reloadFolder(item);
            }
        });
    }

    // Define HGrid Button Actions
    HGrid.Actions['releaseStudy'] = {
        on: 'click',
        callback: function (evt, row) {
            var self = this;
            var url = row.urls.release;
            bootbox.confirm({
                title: 'Release this study?',
                message: 'By releasing this study, all content will be ' +
                    'made available through the Harvard Dataverse using their ' +
                    'internal privacy settings, regardless of your OSF project ' +
                    'settings. Are you sure you want to release this study?',
                callback: function(result) {
                    if(result) {
                        self.changeStatus(row, Rubeus.Status.RELEASING_STUDY);
                        $.osf.putJSON(
                            url,
                            {}
                        ).done(function() {
                            bootbox.alert('Your study has been released. Please ' +
                            'allow up to 24 hours for the released version to ' +
                            'appear on your OSF project\'s file page.');
                            self.updateItem(row);
                        }).fail( function(args) {
                            var message = args.responseJSON.code === 400 ?
                                'Error: Something went wrong when attempting to ' +
                                'release your study.' :
                                'Error: This version has already been released.'
                            bootbox.alert(message);
                            self.updateItem(row);
                        });
                    }
                }
            });
        }
    };

    // Register configuration
    Rubeus.cfg.dataverse = {
        // Handle events
        listeners: [
            {
                on: 'change',
                selector: '.dataverse-state-select',
                callback: function(evt, row, grid) {
                    var $this = $(evt.target);
                    var state = $this.val();
                    refreshDataverseTree(grid, row, state);
                }
            }
        ],
        // Update file information for updated files
        uploadSuccess: function(file, row, data) {
            if (data.actionTaken === 'file_updated') {
                var gridData = this.getData();
                for (var i=0; i < gridData.length; i++) {
                    var item = gridData[i];
                    if (item.file_id && data.old_id &&
                        item.file_id === data.old_id) {
                        $.extend(item, data);
                        this.updateItem(item);
                    }
                }
            }
        },
        UPLOAD_ERROR: '<span class="text-danger">The Dataverse could ' +
                        'not accept your file at this time. </span>'
    };

    // Define Fangorn Button Actions
    function _fangornActionColumn (item, col){
        var self = this;
        var buttons = [];

        function _uploadEvent (event, item, col){
            event.stopPropagation();
            this.dropzone.hiddenFileInput.click();
            this.dropzoneItemCache = item;
            console.log('Upload Event triggered', this, event,  item, col);
        }

        function dataverseRelease (event, item, col) {
            var msg = new Fangorn.status(self, item, 'danger', 'Testing message', 1);
            msg.init(); 
            // var self = this; // treebeard
            // var url = item.data.urls.release;
            // bootbox.confirm({
            //     title: 'Release this study?',
            //     message: 'By releasing this study, all content will be ' +
            //         'made available through the Harvard Dataverse using their ' +
            //         'internal privacy settings, regardless of your OSF project ' +
            //         'settings. Are you sure you want to release this study?',
            //     callback: function(result) {
            //         if(result) {
            //             //self.changeStatus(row, Rubeus.Status.RELEASING_STUDY);
            //             $.osf.putJSON(
            //                 url,
            //                 {}
            //             ).done(function(data) {
            //                 bootbox.alert('Your study has been released. Please ' +
            //                 'allow up to 24 hours for the released version to ' +
            //                 'appear on your OSF project\'s file page.');
            //                 //self.updateItem(row);
            //                 console.log("Returned Done:", data);
            //             }).fail( function(args) {
            //                 console.log("Returned error:", args);
            //                 var message = args.responseJSON.code === 400 ?
            //                     'Error: Something went wrong when attempting to ' +
            //                     'release your study.' :
            //                     'Error: This version has already been released.'
            //                 bootbox.alert(message);
            //                 //self.updateItem(row);
            //             });
            //         }
            //     }
            // });
        }

        function _removeEvent (event, item, col) {
            event.stopPropagation();
            console.log('Remove Event triggered', this, event, item, col);
            var tb = this;
            if(item.data.permissions.edit){
                // delete from server, if successful delete from view
                $.ajax({
                  url: item.data.urls.delete,
                  type : 'DELETE'
                })
                .done(function(data) {
                    // delete view
                    tb.deleteNode(item.parentID, item.id);
                    console.log('Delete success: ', data);
                })
                .fail(function(data){
                    console.log('Delete failed: ', data);
                });
            }
        }

        // Download Zip File
        if (item.kind === 'folder' && item.data.addonFullname) {
            buttons.push(
            {
                'name' : '',
                'icon' : 'icon-upload-alt',
                'css' : 'fangorn-clickable btn btn-default btn-xs',
                'onclick' : _uploadEvent
            },
            {
                'name' : 'Release Study',
                'icon' : 'icon-globe',
                'css' : 'btn btn-primary btn-xs',
                'onclick' : dataverseRelease
            }
            );
        } else if (item.kind === 'folder' && !item.data.addonFullname){
            buttons.push(
                {
                    'name' : '',
                    'icon' : 'icon-upload-alt',
                    'css' : 'fangorn-clickable btn btn-default btn-xs',
                    'onclick' : _uploadEvent
                }
            );
        } else if (item.kind === "item"){
            buttons.push({
                'name' : '',
                'icon' : 'icon-download-alt',
                'css' : 'btn btn-info btn-xs',
                'onclick' : function(){window.location = item.data.urls.download}
            },
            {
                'name' : '',
                'icon' : 'icon-remove',
                'css' : 'm-l-lg text-danger fg-hover-hide',
                'style' : 'display:none',
                'onclick' : _removeEvent
            }
            );
        }
        return m('.btn-group', [
                buttons.map(function(btn){  
                    return m('button', { 'data-col' : item.id, 'class' : btn.css, style : btn.style, 'onclick' : function(){ btn.onclick.call(self, event, item, col); } },
                        [ m('span', { 'class' : btn.icon}, ' ' + btn.name) ]);
                })
        ]); 
    }



    function _fangornColumns (item) {
        var columns = []; 
        columns.push({
                data : 'name',
                folderIcons : true,
                custom : function (){ return item.data.name + ' ' + item.data.extra; }
            }); 

      if(this.options.placement === 'project-files') {
        columns.push(
            {
                css : 'action-col',
                custom : _fangornActionColumn
            },
            {
                data  : 'downloads',
                css : ''
            });
        }
        return columns; 
    } 


    function _fangornFolderIcons(item){
            //This is a hack, should probably be changed...
            return m('img',{src:item.data.iconUrl, style:{width:"16px", height:"auto"}}, ' ');
    }


    function _fangornLazyLoad(item){
        if (item.data.urls.fetch){
            return item.data.urls.fetch;
        }
        if(item.urls.fetch) {
            return item.urls.fetch;
        }
        return false;
    }



    Fangorn.config.dataverse = {
        // Handle changing the branch select
        folderIcon: _fangornFolderIcons,
        resolveRows: _fangornColumns,
        lazyload:_fangornLazyLoad
    };


}));
