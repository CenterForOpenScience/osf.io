'use strict';
var $  = require('jquery');
require('jquery.cookie');

$(function(){
    // Make adblock message permanently dismissible
    var adBlockPersistKey = 'adBlockDismiss';
    var $adBlock = $('#adBlock').on('closed.bs.alert', function() {
        $.cookie(adBlockPersistKey, '1', {path: '/'});
    });
    var dismissed = $.cookie(adBlockPersistKey) === '1';
    if (!dismissed) {
        $adBlock.show();
    }
});
