/**
 * Github FileBrowser configuration module.
 */
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
                'name' : '',
                'icon' : 'icon-download-alt',
                'css' : 'fangorn-clickable btn btn-info btn-xs',
                'onclick' : function(){window.location = item.data.urls.zip;}
            },
            {
                'name' : '',
                'icon' : 'icon-external-link',
                'css' : 'btn btn-primary btn-xs',
                'onclick' : function(){window.location = item.data.urls.repo;}//GO TO EXTERNAL PAGE
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
                'onclick' : _downloadEvent
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
        return buttons.map(function(btn){ 
            return m('span', { 'data-col' : item.id }, [ m('i', 
                { 'class' : btn.css, style : btn.style, 'onclick' : function(event){ btn.onclick.call(self, event, item, col); } },
                [ m('span', { 'class' : btn.icon}, btn.name) ])
            ]);
        }); 
    }

    function changeBranch(item, branch){
        var tb = this;
        var url = item.data.urls.branch + '?' + $.param({branch: branch});

        $.ajax({
            type: 'get',
            url: url
        }).done(function(response) {
            console.log("Brach Response", response);
            // Update the item with the new branch data
            var icon = $('.tb-row[data-id="'+item.id+'"]').find('.tb-toggle-icon');
            m.render(icon.get(0), m('i.icon-refresh.icon-spin'));
            item.data = response[0]; 
            $.ajax({
                type: 'get',
                url: response[0].urls.fetch
            }).done(function(data){
                item.children = []; 
                console.log("data", data);
                tb.updateFolder(data, item);
                tb.redraw();
            m.render(icon.get(0), m('i.icon-minus'));
            }).fail(function(xhr, status, error){
                console.log("Error:", xhr, status, error);
            });
        });
    }

    function _fangornGithubTitle (item, col)  {
        // this = treebeard
        var tb = this;
        var branchArray = [];
        if (item.data.branches){
            for (var i = 0; i < item.data.branches.length; i++){
                var selected = item.data.branches[i] === 'master' ? 'selected' : ''; 
                branchArray.push(m("option", {selected : selected, value:item.data.branches[i]}, item.data.branches[i]));
            }
        }

        if (item.data.addonFullname){
            return m("span",[
                m("github-name", item.data.name + ' '),
                m("span",[
                    m("select[name=branch-selector]", { onchange: function(ev) { changeBranch.call(tb, item, ev.target.value ) } }, branchArray)
                ])
            ]);
        } else {
            return m("span",[
                m("github-name",{onclick: function(){window.location = item.data.urls.view}}, item.data.name)
            ]);
        }

    }

    function _fangornColumns (item) {
        var columns = []; 
        columns.push({
                data : 'name',
                folderIcons : true,
                filter: true,
                custom : _fangornGithubTitle
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

    function _fangornLazyLoad(item){
        if (item.data.urls.fetch){
            return item.data.urls.fetch;
        }
        if(item.urls.fetch) {
            return item.urls.fetch;
        }
        return false;
    }

    function _fangornFolderIcons(item){
        if(item.data.iconUrl){
            return m('img',{src:item.data.iconUrl, style:{width:"16px", height:"auto"}}, ' ');
        }
        return undefined;            
    }

    function _fangornUploadComplete(item){
        console.log('upload complete', this, item);
        var index = this.returnIndex(item.id);
        // item.open = false;
        // item.load = false;
        //this.toggleFolder(index, null);
            
    }

    // Register configuration
    Fangorn.config.github = {
        // Handle changing the branch select
        folderIcon: _fangornFolderIcons,
        resolveRows: _fangornColumns,
        lazyload: _fangornLazyLoad,
        onUploadComplete : _fangornUploadComplete
    };

