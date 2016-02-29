/**
 * Initialization code for the home page.
 */

'use strict';

var $ = require('jquery');
var m = require('mithril');

var quickSearchProject = require('js/quickProjectSearchPlugin');
var newAndNoteworthy = require('js/newAndNoteworthyPlugin');
var meetingsAndConferences = require('js/meetingsAndConferencesPlugin');
var LogWrap = require('js/recentActivityWidget');


$(document).ready(function(){
    m.mount(document.getElementById('newAndNoteworthyWrap'), m.component(newAndNoteworthy, {}));
    m.mount(document.getElementById('hostingAMeetingWrap'), m.component(meetingsAndConferences, {}));
    m.mount(document.getElementById('addQuickProjectSearchWrap'), m.component(quickSearchProject, {}));
    m.mount(document.getElementById('recentActivityWidget'), m.component(LogWrap, {wrapper: 'recentActivity'}));
});
