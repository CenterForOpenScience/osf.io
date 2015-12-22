/**
 * UI and function to quick search projects
 */

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');

// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
}

var quickSearchProject = {
    controller: function(options){
        var self = this;
    },
    view: function(ctrl, options){

    }
};

module.exports = quickSearchProject;