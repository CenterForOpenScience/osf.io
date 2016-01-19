/**
 * Initialization code for the home page.
 */

'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var quickSearchProject = require('js/quickProjectSearchPlugin');
var newAndNoteworthy = require('js/newAndNoteworthyPlugin');
var meetingsAndConferences = require('js/meetingsAndConferencesPlugin');
var m = require('mithril');

$(document).ready(function(){
    m.mount(document.getElementById('addQuickProjectSearchWrap'), m.component(quickSearchProject, {}));
    m.mount(document.getElementById('newAndNoteworthyWrap'), m.component(newAndNoteworthy, {}));
    m.mount(document.getElementById('hostingAMeetingWrap'), m.component(meetingsAndConferences, {}));
});