// website/static/js/growlBox.js
'use strict';
var $ = require('jquery');
require('bootstrap.growl');

var oop = require('js/oop');

/**
* Show a growl-style notification for messages. Defaults to an error type.
* @param {String} title Shows in bold at the top of the box. Required or it looks foolish.
* @param {String} message Shows a line below the title. This could be '' if there's nothing to say.
* @param {String} type One of 'success', 'info', 'warning', or 'danger'. Defaults to danger.
* @param {Number} delay if provided the number of miliseconds before message disappears
 */
var GrowlBox = oop.defclass({
    constructor: function(title, message, type, delay) {
        this.title = title;
        this.message = message;
        this.type = type || 'danger';
        this.delay = delay || 0;
        this.show();
    },
    show: function() {
        $.growl({
            title: '<strong>' + this.title + '<strong><br />',
            message: this.message
        },{
            type: this.type,
            delay: this.delay,
            animate: {
                enter: 'animated fadeInDown',
                exit: 'animated fadeOut'
            }
        });

    }
});

module.exports = GrowlBox;
