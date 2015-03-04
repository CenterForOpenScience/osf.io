'use strict';

var $ = require('jquery');
var ZeroClipboard = require('zeroclipboard');

ZeroClipboard.config({
    swfPath: '/static/vendor/bower_components/zeroclipboard/dist/ZeroClipboard.swf'
});

var makeClient = function(elm) {
    var $elm = $(elm);
    var client = new ZeroClipboard(elm);

    $elm.on('mouseover', function() {
        $elm.addClass('active');
    });
    $elm.on('mouseout', function() {
        $elm.removeClass('active');
    });

    client.on('aftercopy', function() {
        $elm.blur();
        $elm.tooltip('hide');
    });

    return client;
};

module.exports = makeClient;
