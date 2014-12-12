/**
 * Created by faye on 11/6/14.
 */
var m = require('mithril'); 

var Fangorn = require('fangorn');


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

    function _fangornUploadSuccess(file, item, response){
        var self = this;
        var parent = item.parent();
        item.data.name = file.name; 
        item.data.urls = {
            'delete': parent.data.nodeApiUrl + 's3/' + file.destination + '/',
            'download': parent.data.nodeUrl + 's3/' + file.destination + '/download/',
            'view': parent.data.nodeUrl + 's3/' + file.destination + '/'
        };
        item.data.permissions = parent.data.permissions; 
        return item; 
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


