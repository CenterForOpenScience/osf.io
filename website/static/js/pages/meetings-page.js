var $ = require('jquery');
var m = require('mithril');
var Meetings = require('../meetings.js');
var Submissions = require('../submissions.js');

new Meetings(window.contextVars.meetings);

var request = $.getJSON('/api/v1/meetings/submissions/');
var DonateBanner = require('js/home-page/donateBannerPlugin');
var columnSizeClass = '.col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2';

request.always(function() {
    $('#allMeetingsLoader').hide();
});
request.done(function(data) {
    new Submissions(data.submissions);
});

$(document).ready(function(){
    var osfDonateBanner = {
        view : function(ctrl, args) {
            return [
                m(DonateBanner.background, m('.container',
                    [
                        m('.row', [
                            m(columnSizeClass,  m.component(DonateBanner.Banner, {}))
                        ])
                    ]
                )),
            ];
        }
    };
    m.mount(document.getElementById('osfDonateBanner'), m.component(osfDonateBanner, {}));
});
