;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['js/fangorn'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('fangorn', function() { factory(Fangorn); });
    } else { factory(Fangorn); }
}(this, function(Fangorn) {


    function _fangornFolderIcons(item){
            //This is a hack, should probably be changed...
            return m('img',{src:item.data.iconUrl, style:{width:"16px", height:"auto"}}, ' ');
    }


    Fangorn.config.dropbox = {
        // Custom error message for when folder contents cannot be fetched
        /*FETCH_ERROR: '<span class="text-danger">This Dropbox folder may ' +
                        'have been renamed or deleted. ' +
                        'Please select a folder at the settings page.</span>'*/
                        // /static/addons/dropbox/comicon.png
        folderIcon: _fangornFolderIcons
    };

}));

