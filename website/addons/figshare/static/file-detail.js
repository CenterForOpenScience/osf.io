var DeleteFile = require('../../../static/js/deleteFile.js');

new DeleteFile('#figshareScope', window.contextVars.node.urls);

$(function () {
    $("[data-toggle='popover']").popover(({html:true}));
    $("[data-toggle='popover'].disabled").css("pointer-events", "auto")
 });