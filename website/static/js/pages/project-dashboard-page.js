/** Initialization code for the project dashboard. */
var Rubeus = require('rubeus');

// Initialize the filebrowser
new Rubeus('#myGrid', {
    data: nodeApiUrl + 'files/grid/',
    columns: [Rubeus.Col.Name],
    uploads: false,
    width: "100%",
    height: 600,
    progBar: '#filetreeProgressBar',
    searchInput: '#fileSearch'
});
