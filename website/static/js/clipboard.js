'use strict';

var $ = require('jquery');
var ZeroClipboard = require('zeroclipboard');
var m = require('mithril');

ZeroClipboard.config({
    swfPath: '/static/vendor/bower_components/zeroclipboard/dist/ZeroClipboard.swf'
});

var makeClipboardClient = function(elm) {
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

function generateClipboard(url){

    var cb = function(elem) {
        makeClipboardClient(elem);
    };
    return m('div.input-group[style="width: 180px"]',
                       [
                           m('span.input-group-btn',
                               m('button.btn.btn-default.btn-sm[type="button"][data-clipboard-text="'+url+ '"]', {config: cb},
                                   m('.fa.fa-copy')
                               )
                           ),
                           m('input[value="'+url+'"][readonly="readonly"][style="height: 30px;color:#333333;"]')
                       ]
           );
}

module.exports = {
                    generateClipboard:generateClipboard,
                    makeClipboardClient:makeClipboardClient
                 };
