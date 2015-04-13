'use strict';

var m = require('mithril');
var Fangorn = require('js/fangorn');

function _fangornLazyLoadError(item) {
    item.notify.update('Google Drive couldn\'t load, please try again later.', 'deleting', undefined, 3000);
    return true;
}

Fangorn.config.googledrive = {
    lazyLoadError : _fangornLazyLoadError
};
