var $ = require('jquery');
$('input[name=q]').remove();

var Search = require('../search.js');
new Search('#searchControls', '/api/v1/search/', '');
