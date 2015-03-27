var nodeApiUrl = window.contextVars.node.urls.api;

var fileBrowser = require('../fileViewTreebeard.js');
var FileRenderer = require('../filerenderer.js');
var FileRevisions = require('../fileRevisions.js');

if (window.contextVars.renderURL !== undefined) {
    FileRenderer.start(window.contextVars.renderURL, '#fileRendered');
}

new FileRevisions(
    '#fileRevisions',
    window.contextVars.node,
    window.contextVars.file,
    window.contextVars.currentUser.canEdit
);

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
    $('.panel-collapse').on('click', function () {
        var panelHeight = $('.osf-panel.hidden-xs').height();
        var el = $(this).closest('.panel-toggle');
        el.children('.osf-panel.hidden-xs').hide();
        panelToggle.removeClass('col-md-3').addClass('col-md-1');
        panelExpand.removeClass('col-md-6').addClass('col-md-8');
        el.children('.panel-collapsed').show();
        el.children('.panel-collapsed').css('height', panelHeight);
    });
    $('.panel-collapsed .osf-panel-header').on('click', function () {
        var el = $(this).parent();
        var toggle = el.closest('.panel-toggle');
        toggle.children('.osf-panel').show();
        el.hide();
        panelToggle.removeClass('col-md-1').addClass('col-md-3');
        panelExpand.removeClass('col-md-8').addClass('col-md-6');
    });
});