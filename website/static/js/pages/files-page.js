<<<<<<< HEAD
var Rubeus = require('rubeus');
var Comment = require('../comment.js');
=======
var Fangorn = require('fangorn');
>>>>>>> f06b14bf9b01c7a00a6f36a13eee129f9344998e

// Don't show dropped content if user drags outside grid
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };

var nodeApiUrl = window.contextVars.node.urls.api;

$(document).ready(function(){
	// Fangorn load 	
	 $.ajax({
      url:  nodeApiUrl + 'files/grid/'
    })
    .done(function( data ) {
            var fangornOpts = {
                placement : 'project-files',
                divID: 'treeGrid',
                filesData: data.data
            };
            var filebrowser = new Fangorn(fangornOpts);
        });

})
