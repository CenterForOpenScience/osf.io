var $ = require('jquery');
$('input[name=q]').remove();

var Search = require('../search.js');
//TODO This needs to be modular/generic
var search =  new Search('#searchControls', '/api/v1/search/', '/api/v1/app/6qajn/');
