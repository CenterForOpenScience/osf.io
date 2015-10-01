'use strict';
var $ = require('jquery');

var fileBrowser = require('../fileViewTreebeard');
var nodeApiUrl = window.contextVars.node.urls.api;

$(document).ready(function() {


    var panelToggle = $('.panel-toggle');
    var panelExpand = $('.panel-expand');
    var panelVisible = panelToggle.find('.osf-panel-hide');
    var panelHidden = panelToggle.find('.osf-panel-show');
    var fileNav = $('#file-navigation');

    var initFileBrowser = function () {
        $.ajax({
            url: nodeApiUrl + 'files/grid/'
        })
        .done(function (data) {
            new fileBrowser(data);
            fileNav.data('file-browser-init', true);
        });
    };

    $('.osf-panel-hide .panel-heading').on('click', function (e) {
        $(e.target).parents('.col-sm-4').removeClass('col-sm-4').addClass('col-sm-2');
        panelExpand.removeClass('col-sm-8').addClass('col-sm-10');

        panelVisible.hide();
        panelHidden.show();
    });
    $('.osf-panel-show .panel-heading').on('click', function (e) {
        $(e.target).parents('.col-sm-2').removeClass('col-sm-2').addClass('col-sm-4');
        panelExpand.removeClass('col-sm-11').addClass('col-sm-8');

        panelVisible.show();
        panelHidden.hide();

        if (!fileNav.data('file-browser-init')) {
            initFileBrowser();
        }
    });
    $('.osf-panel-hide .panel-heading').on('click', 'input', function(e) {
        e.stopPropagation();
    });
    // TODO: This is a hack to highlight the "Files" tab. Rethink.
    $('.osf-project-navbar li#projectNavFiles').addClass('active');

});
