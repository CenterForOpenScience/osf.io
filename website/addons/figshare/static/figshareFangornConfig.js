var m = require('mithril'); 

var Fangorn = require('fangorn');


    // Define Fangorn Button Actions
    function _fangornActionColumn (item, col){
        var self = this;
        var buttons = [];

        function _uploadEvent (event, item, col){
            event.stopPropagation();
            this.dropzone.hiddenFileInput.click();
            this.dropzoneItemCache = item;
            this.updateFolder(null, item);  
            console.log('Upload Event triggered', this, event,  item, col);
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

        function _downloadEvent (event, item, col) {
            event.stopPropagation();
            console.log('Download Event triggered', this, event, item, col);
            window.location = item.data.urls.download;
        }


        if (item.kind === 'folder'){
            buttons.push(
                {
                    'name' : '',
                    'icon' : 'icon-upload-alt',
                    'css' : 'fangorn-clickable btn btn-default btn-xs',
                    'onclick' : _uploadEvent
                }
            );
        } 

        if (item.kind === "item" && item.data.permissions && item.data.permissions.download){
            buttons.push({
                'name' : '',
                'icon' : 'icon-download-alt', 
                'css' : 'btn btn-info btn-xs',
                'onclick' : _downloadEvent
            });
        }

        if (item.kind === "item"){
            buttons.push({
                    'name' : '',
                    'icon' : 'icon-remove',
                    'css' : 'm-l-lg text-danger fg-hover-hide',
                    'style' : 'display:none',
                    'onclick' : _removeEvent
                });            
        }

        
        return buttons.map(function(btn){ 
            return m('span', { 'data-col' : item.id }, [ m('i', 
                { 'class' : btn.css, style : btn.style, 'onclick' : function(event){ btn.onclick.call(self, event, item, col); } },
                [ m('span', { 'class' : btn.icon}, btn.name) ])
            ]);
        }); 
    }

    function _fangornTitleColumn (item, col) {
        return m('span', 
            { onclick : function(){ 
                if (item.kind === 'item') {
                    window.location = item.data.urls.view;                    
                } 
            }}, 
            item.data.name);
    }
    

    function _fangornColumns (item) {
        var columns = []; 
        columns.push({
                data : 'name',
                folderIcons : true,
                filter: true,
                custom : _fangornTitleColumn
        }); 

      if(this.options.placement === 'project-files') {
        columns.push(
            {
                css : 'action-col',
                filter : false,
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

    Fangorn.config.figshare = {
        resolveRows: _fangornColumns
    };


