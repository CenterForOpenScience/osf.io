'use strict';

var $ = require('jquery');
var Clipboard = require('clipboard');

var setTooltip = function (elm, message) {
    $(elm).tooltip('hide')
    .attr('title', message)
    .tooltip('show');
};

var hideTooltip = function (elm) {
    setTimeout(function() {
        $(elm).tooltip('hide');
    }, 2000);
};

var makeClient = function(elm) {
    var $elm = $(elm);

    var client = new Clipboard(elm);

    client.on('success', function(e){
        setTooltip(e.trigger, 'Copied!');
        hideTooltip(e.trigger);
    });

    client.on('error', function(e){
        setTooltip(e.trigger, 'Copy failed!');
        hideTooltip(e.trigger);
    });

    return client;
};

module.exports = makeClient;
