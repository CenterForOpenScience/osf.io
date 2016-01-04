var $ = require('jquery');
var m = require('mithril');
var LogWrap = require('js/recentActivityWidget');

$(document).ready(function() {
    m.mount(document.getElementById('recentActivityWidget'), m.component(LogWrap, {userId: window.contextVars.userId}));
});
