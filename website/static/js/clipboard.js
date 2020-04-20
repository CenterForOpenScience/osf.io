'use strict';

var $ = require('jquery');
var Clipboard = require('clipboard');

var _ = require('js/rdmGettext')._;

var setTooltip = function (elm, message) {
    $(elm).tooltip('hide')
    .attr('title', message)
    .attr('data-container', 'body')
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
        setTooltip(e.trigger, _('Copied!'));
        hideTooltip(e.trigger);
    });

    client.on('error', function(e){
        setTooltip(e.trigger, _('Copy failed!'));
        hideTooltip(e.trigger);
    });

    return client;
};

module.exports = makeClient;
