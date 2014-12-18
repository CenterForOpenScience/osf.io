var Rubeus = require('rubeus');

// Don't show dropped content if user drags outside grid
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };

// Initialize the filebrowser
new Rubeus('#myGrid', {
    data: window.contextVars.node.urls.api + 'files/grid',
    searchInput: '#fileSearch',
    uploads: true
});
