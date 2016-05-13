'use strict';
var $  = require('jquery');
var Cookie = require('js-cookie');
var keenAnalysis = require('keen-analysis');
var ProjectUsageStatistics = require('js/statistics');

$(function(){
    // Make adblock message permanently dismissible
    var adBlockPersistKey = 'adBlockDismiss';
    var $adBlock = $('#adBlock').on('closed.bs.alert', function() {
        Cookie.set(adBlockPersistKey, '1', {path: '/'});
    });
    var dismissed = Cookie.get(adBlockPersistKey) === '1';
    if (!dismissed) {
        $adBlock.show();
    }
});

keenAnalysis.ready(function(){
    new ProjectUsageStatistics();
});
