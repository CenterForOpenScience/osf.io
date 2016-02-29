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
    var osfHome = {
        view : function(ctrl, args) {
            return [
                m('.quickSearch', m.component(quickSearchProject, {})),
                m('.recentActvity', m.component(LogWrap, {wrapper: 'recentActivity'})),
                m('.newAndNoteworthy', m.component(newAndNoteworthy, {})),
                m('.meetings', m.component(meetingsAndConferences, {}))
                ];
        }
    };
    // If logged in...
    m.mount(document.getElementById('osfHome'), m.component(osfHome, {}));



});
