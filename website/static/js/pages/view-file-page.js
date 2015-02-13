var m = require('mithril');
var FileViewPage = require('../viewFile.js');

// TODO: Workaround for highlighting the Files tab in the project navbar. Rethink.
$(document).ready(function(){
    $('.osf-project-navbar li:contains("Files")').addClass('active');
});

m.module(document.getElementById('fileViewPage'), FileViewPage);
