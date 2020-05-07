var $ = require('jquery');
$('input[name=q]').remove();

// floating filter panel
$(document).ready(function() {
    var $affixFilter = $('div[data-spy="affix"]');
    $affixFilter.width($affixFilter.parent().width());
});
$(window).resize(function() {
    var $affixFilter = $('div[data-spy="affix"]');
    $affixFilter.width($affixFilter.parent().width());
});

var Search = require('../search-grdm.js');
require('../../css/search-bar.css');
new Search('#searchControls', '/api/v1/search/', '');
