'use strict';

var m = require('mithril');
var Fangorn = require('js/fangorn');

function _fangornLazyLoadError (item) {
    item.notify.update('Dropbox couldn\'t load, please try again later.', 'deleting', undefined, 3000);
    return true;
}

Fangorn.config.dropbox = {
    lazyLoadError : _fangornLazyLoadError
};
