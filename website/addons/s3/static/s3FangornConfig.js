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

Fangorn.config.s3 = {
    folderIcon: _fangornFolderIcons,
};


