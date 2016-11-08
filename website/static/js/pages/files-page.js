'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Fangorn = require('js/fangorn').Fangorn;
var node = window.contextVars.node;

// Don't show dropped content if user drags outside grid
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };

var nodeApiUrl = window.contextVars.node.urls.api;

$(document).ready(function(){
    $.ajax({
      url: nodeApiUrl + 'files/grid/'
    }).done(function(data) {
        new Fangorn({
            placement: 'project-files',
            divID: 'treeGrid',
            filesData: data.data,
            allowMove: !node.isRegistration,
            xhrconfig: $osf.setXHRAuthorization
        });
    });
});
