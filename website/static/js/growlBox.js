// website/static/js/growlBox.js
'use strict';
var $ = require('jquery');
require('bootstrap.growl');

/**
* Show a growl-style notification for messages. Defaults to an error type.
* @param {String} title Shows in bold at the top of the box. Required or it looks foolish.
* @param {String} message Shows a line below the title. This could be '' if there's nothing to say.
* @param {String} type One of 'success', 'info', 'warning', or 'danger'. Defaults to danger.
*/
function GrowlBox (title, message, type) {
    var self = this;
    self.type = type || 'danger';
    self.title = title;
    self.message = message;
    self.init(self);
}
GrowlBox.prototype.init = function(self) {
    $.growl({
        title: '<strong>' + self.title + '<strong><br />',
        message: self.message
    },{
        type: self.type,
        delay: 0,
        animate: {
            enter: 'animated slideInDown',
            exit: 'animated slideOutRight'
        }
    });
};

module.exports = GrowlBox;
