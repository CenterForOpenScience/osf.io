/**
 * Created by faye on 11/6/14.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['js/fangorn'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('fangorn', function() { factory(Fangorn); });
    } else { factory(Fangorn); }
}(this, function(Fangorn) {

    function _fangornFolderIcons(item){
        if(item.data.addonFullname){
            //This is a hack, should probably be changed...
            return m('img',{src:item.data.iconUrl, style:{width:"16px", height:"auto"}}, ' ');
        }
    }

    function _fangornLazyLoad(item){
        window.console.log("Fangorn Lazy Load URL", item.data.urls.fetch);
        return item.data.urls.fetch;
    }

    function _fangornUploadAdd(file, item){
        //console.log("fangornUploadAdd", file, item);
        var self = this;
        var parent = item;
        var name = file.name;

        // Make it possible to upload into subfolders
        while (parent.depth > 1 && !parent.data.isAddonRoot) {
            name = parent.name + '/' + name;
            parent = parent.parent();
        }
        file.destination = name;
        file.signedUrlFrom = parent.data.urls.upload;
    }

    function _fangornUploadSending(file, xhr, fomData){
        xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
        xhr.setRequestHeader('x-amz-acl', 'private');
    }

    function _fangornUploadSuccess(file, item){
        var self = this;
        var parent = item.parent();
        item.data.urls = {
            'delete': parent.nodeApiUrl + 's3/' + file.destination + '/',
            'download': parent.nodeUrl + 's3/' + file.destination + '/download/',
            'view': parent.nodeUrl + 's3/' + file.destination + '/'
        };
        item.data.permissions = parent.permissions;
        /*this.updateItem(row);
        var updated = Rubeus.Utils.itemUpdated(row, parent);
        if (updated) {
            self.changeStatus(row, Rubeus.Status.UPDATED);
            self.delayRemoveRow(row);
        } else {
            self.changeStatus(row, Rubeus.Status.UPLOAD_SUCCESS, null, 2000,
                function(row) {
                    self.showButtons(row);
                });
        }*/
    }

    Fangorn.config.s3 = {
        folderIcon: _fangornFolderIcons,
        lazyload: _fangornLazyLoad,
        uploadMethod: 'PUT',
        uploadUrl: null,
        uploadAdd: _fangornUploadAdd,
        uploadSending: _fangornUploadSending,
        uploadSuccess: _fangornUploadSuccess
    };

}));
