var $ = require('jquery');
$('input[name=q]').remove();

var Search = require('js/search.js');
new Search('#searchControls', '/api/v1/search/', '');
