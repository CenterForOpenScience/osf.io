'use strict';
var $ = require('jquery');

var fileBrowser = require('../fileViewTreebeard');
var nodeApiUrl = window.contextVars.node.urls.api;

$(document).ready(function() {
    // Treebeard Files view
    $.ajax({
        url: nodeApiUrl + 'files/grid/'
    })
    .done(function (data) {
        new fileBrowser(data);
    });

    var panelToggle = $('.panel-toggle');
    var panelExpand = $('.panel-expand');
    var panelVisible = panelToggle.find('.osf-panel-hide');
    var panelHidden = panelToggle.find('.osf-panel-show');

    $('.panel-collapse').on('click', function () {
        panelToggle.removeClass('col-sm-3').addClass('col-sm-1');
        panelExpand.removeClass('col-sm-9').addClass('col-sm-11');

        panelVisible.hide();
        panelHidden.show();
    });
    $('.osf-panel-show .osf-panel-header').on('click', function () {
        panelToggle.removeClass('col-sm-1').addClass('col-sm-3');
        panelExpand.removeClass('col-sm-11').addClass('col-sm-9');

        panelVisible.show();
        panelHidden.hide();
    });

});
