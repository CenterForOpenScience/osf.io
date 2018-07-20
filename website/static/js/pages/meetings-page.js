var $ = require('jquery');
var m = require('mithril');
var Meetings = require('../meetings.js');
var Submissions = require('../submissions.js');

new Meetings(window.contextVars.meetings);

var request = $.getJSON('/api/v1/meetings/submissions/');
var ScheduledBanner = require('js/home-page/scheduledBannerPlugin');
var columnSizeClass = '.col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2';

request.always(function() {
    $('#allMeetingsLoader').hide();
});
request.done(function(data) {
    new Submissions(data.submissions);
});

$(document).ready(function(){
    var osfScheduledBanner = {
        view : function(ctrl, args) {
            return [
                m('.scheduled-banner-background', m('.container',
                    [
                        m(columnSizeClass, m.component(ScheduledBanner, {}))
                    ]
                )),
            ];
        }
    };
    m.mount(document.getElementById('osfScheduledBanner'), m.component(osfScheduledBanner, {}));
});
