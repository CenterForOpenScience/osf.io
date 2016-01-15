/**
 * UI and function to quick search projects
 */

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var nodeModule = require('js/quickProjectSearchPlugin');

// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
};


var newAndNoteworthy = {
    controller: function() {
    },
    view : function(ctrl) {

    }
};

module.exports = newAndNoteworthy;

