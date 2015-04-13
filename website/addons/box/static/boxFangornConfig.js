'use strict';

var m = require('mithril');
var Fangorn = require('js/fangorn');

function _fangornLazyLoadError (item) {
    item.notify.update('Box couldn\'t load, please try again later.', 'deleting', undefined, 3000);
    return true;
}

Fangorn.config.box = {
    lazyLoadError : _fangornLazyLoadError
};
