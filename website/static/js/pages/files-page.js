var Fangorn = require('fangorn');

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
