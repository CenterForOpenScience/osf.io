'use strict';

require('font-awesome-webpack');
require('../../vendor/bower_components/bootstrap/dist/js/bootstrap.js');
require('../../vendor/bower_components/admin-lte/dist/js/app.min.js');

var $ = require('jquery');

// Function to adjust content height
function adjustContentHeight() {
    // Get the sidebar and content div
    var sidebar = $('section.sidebar');
    var contentWrapper = $('div.content-wrapper');
    var content = $('section.content');

    // Get the height of the sidebar
    var sidebarHeight = sidebar.height();

    if (sidebarHeight <= screen.height) {
        // If the sidebar height is less than or equal to the screen height, then return
        return;
    }

    // Get the height of the content
    var contentHeight = content.outerHeight();
    if (contentHeight < sidebarHeight) {
        // If the content height is less than the sidebar height, set the content height to the sidebar height
        contentWrapper.css('min-height', sidebarHeight + 'px');
    } else {
        // Otherwise, set the content height to the content height
        contentWrapper.css('min-height', contentHeight + 'px');
    }
}

// When the submenu is shown (expanded), adjust the content height
$('.collapse').on('shown.bs.collapse', function () {
    adjustContentHeight();
});

// When the submenu is hidden (collapsed), adjust the content height
$('.collapse').on('hidden.bs.collapse', function () {
    adjustContentHeight();
});
