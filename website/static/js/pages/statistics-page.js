$(function(){
    // Ad script alert
    var adBlockPersistKey = 'adBlock';
    var $adBlock = $('#adBlock').on('closed.bs.alert', function() {
        $.cookie(adBlockPersistKey, '0', { expires: 1, path: '/'});
    });
    var dismissed = $.cookie(adBlockPersistKey) === '0';
    if (!dismissed) {
        $adBlock.show();
    }
    // Ad script alert
});
