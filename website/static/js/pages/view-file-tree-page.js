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

    //TODO: Refactor to remove duplication with the wiki menu panel
    var panelToggle = $('.panel-toggle');
    var panelExpand = $('.panel-expand');
    $('.panel-collapse').on('click', function () {
        var panelHeight = $('.osf-panel.hidden-xs').height();
        var el = $(this).closest('.panel-toggle');
        el.children('.osf-panel.hidden-xs').hide();
        panelToggle.removeClass('col-lg-3').addClass('col-lg-1');
        panelExpand.removeClass('col-lg-9').addClass('col-lg-11');
        el.children('.panel-collapsed').show();
        el.children('.panel-collapsed').css('height', panelHeight);
    });
    $('.panel-collapsed .osf-panel-header').on('click', function () {
        var el = $(this).parent();
        var toggle = el.closest('.panel-toggle');
        toggle.children('.osf-panel').show();
        el.hide();
        panelToggle.removeClass('col-lg-1').addClass('col-lg-3');
        panelExpand.removeClass('col-lg-11').addClass('col-lg-9');
    });

});
