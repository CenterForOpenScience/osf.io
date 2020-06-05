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

// Session settings for sort and results size
$(window).on('load', function() {
    if (window.contextVars.searchSort !== null) {
        var sortPullDown = $('#sortPullDownMenu')[0];
        for (var i = 0; i < sortPullDown.children.length; i++) {
            if (sortPullDown.children[i].value === window.contextVars.searchSort) {
                sortPullDown.children[i].selected = true;
                break;
            }
        }
    }

    if (window.contextVars.searchSize !== null) {
        if (Number.isInteger(window.contextVars.searchSize)) {
            var sizePullDown = $('#resultsPerPagePullDownMenu')[0];
            for (var j = 0; j < sizePullDown.children.length; j++) {
                if (Number(sizePullDown.children[j].value) === window.contextVars.searchSize) {
                    sizePullDown.children[j].selected = true;
                    break;
                }
            }
        }
    }
});

var makeClient = require('js/clipboard');
makeClient('.btn');
var Search = require('../search-grdm.js');
require('../../css/search-bar.css');
new Search('#searchControls', '/api/v1/search/', '');
