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
*/
var GrowlBox = oop.defclass({
    constructor(title, message, type='danger') {
        this.title = title;
        this.message = message;
        this.type = type;
        this.show();
    },
    show() {
        $.growl({
            title: '<strong>' + this.title + '<strong><br />',
            message: this.message
        },{
            type: this.type,
            delay: 0,
            animate: {
                enter: 'animated slideInDown',
                exit: 'animated slideOutRight'
            }
        });

    }
});

module.exports = GrowlBox;
