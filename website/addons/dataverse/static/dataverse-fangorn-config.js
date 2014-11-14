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
            var self = this; // treebeard
            var url = item.data.urls.release;
            var modalContent = [ 
                m('h3', 'Release this study?'), 
                m('p.m-md', 'By releasing this study, all content will be made available through the Harvard Dataverse using their internal privacy settings, regardless of your OSF project settings.'), 
                m('p.font-thick.m-md', 'Are you sure you want to release this study?')
            ];
            var modalActions = [
                m('button.btn.btn-default.m-sm', { 'onclick' : function (){ self.modal.dismiss(); }},'Cancel'),
                m('button.btn.btn-primary.m-sm', { 'onclick' : function() { releaseStudy(); } }, 'Release Study')
            ];

            this.modal.update(modalContent, modalActions); 

            function releaseStudy () {
                self.modal.dismiss();
                item.notify.update('Releasing Study', 'info', 1, 3000);
                $.osf.putJSON(
                    url,
                    {}
                ).done(function(data) {
                    var modalContent = [ 
                        m('p.m-md', 'Your study has been released. Please allow up to 24 hours for the released version to appear on your OSF project\'s file page.')
                    ];
                    var modalActions = [
                        m('button.btn.btn-primary.m-sm', { 'onclick' : function() { self.modal.dismiss(); } }, 'Okay')
                    ];
                    self.modal.update(modalContent, modalActions); 
                }).fail( function(args) {
                    console.log("Returned error:", args);
                    var message = args.responseJSON.code === 400 ?
                        'Error: Something went wrong when attempting to release your study.' :
                        'Error: This version has already been released.';

                    var modalContent = [ 
                        m('p.m-md', message)
                    ];
                    var modalActions = [
                        m('button.btn.btn-primary.m-sm', { 'onclick' : function() { self.modal.dismiss(); } }, 'Okay')
                    ];
                    self.modal.update(modalContent, modalActions); 
                    //self.updateItem(row);
                });
            } 
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
                'name' : ' Release Study',
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
                    return m('i', { 'data-col' : item.id, 'class' : btn.css, style : btn.style, 'onclick' : function(){ btn.onclick.call(self, event, item, col); } },
                        [ m('span', { 'class' : btn.icon}, btn.name) ]);
                })
        ]); 
    }



    function _fangornColumns (item) {
        var columns = []; 
        columns.push({
                data : 'name',
                folderIcons : true,
                filter : true,
                custom : function (){ 
                    return m("span",[
                        m("github-name",{onclick: function(){window.location = item.data.urls.view}}, item.data.name)
                    ]);
                 }
            }); 

      if(this.options.placement === 'project-files') {
        columns.push(
            {
                css : 'action-col',
                filter: false,
                custom : _fangornActionColumn
            },
            {
                data  : 'downloads',
                filter : false,
                css : ''
            });
        }
        return columns; 
    } 

    function _fangornFolderIcons(item){
        if(item.data.iconUrl){
            return m('img',{src:item.data.iconUrl, style:{width:"16px", height:"auto"}}, ' ');
        }
        return undefined;  
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
