'use strict';
$(function(){
    // Ad script alert
    var adBlockPersistKey = 'adBlockDismiss';
    var $adBlock = $('#adBlock').on('closed.bs.alert', function() {
        $.cookie(adBlockPersistKey, '1', {path: '/'});
    });
    var dismissed = $.cookie(adBlockPersistKey) === '1';
    if (!dismissed) {
        $adBlock.show();
    }
    // Ad script alert
});
