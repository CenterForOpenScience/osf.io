var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/donate-banner.css');
require('css/meetings-and-conferences.css');

var currentDate = new Date();

var bannerOptions = [
    {
        startDate: new Date(2017, 7, 7),
        endDate: new Date(2017, 7, 14),
        beforeLink: 'The Center for Open Science (COS) created the OSF and a suite of of free products to advance the ' +
            'work of the research community. If you value these tools, please make a gift to support COS’s efforts to ' +
            'improve and scale these services. ',
        linkText: 'Donate now!',
        afterLink: '',
        background:'.donate-banner.week-1'
    }, {
        startDate: new Date(2017, 7, 14),
        endDate: new Date(2017, 7, 21),
        beforeLink: 'Thousands of researchers use the OSF and its related services daily. If you value the OSF, ',
        linkText: 'make a donation',
        afterLink: ' to support the Center for Open Science and its ongoing efforts to improve and advance these ' +
            'public goods.',
        background:'.donate-banner.week-2'

    }, {
        startDate: new Date(2017, 7, 21),
        endDate: new Date(2017, 7, 28),
        beforeLink: 'The Center for Open Science (COS) created the OSF and its related services as public goods. While' +
            ' these services will always be free to use they are not free to build, improve and maintain. Please ',
        linkText: 'support the OSF and COS with a donation today.',
        afterLink: '',
        background:'.donate-banner.week-3'

    }, {
        startDate: new Date(2017, 7, 28),
        endDate: new Date(2017, 8, 4),
        beforeLink: 'The Center for Open Science launched the OSF with the goal of creating a service where the entire' +
            ' research cycle is supported and barriers to accessing data are removed. ',
        linkText: 'Support COS’s efforts',
        afterLink: ' to advance the work of researchers with a gift today!',
        background:'.donate-banner.week-4'

    }, {
        startDate: new Date(2017, 8, 4),
        endDate: new Date(2017, 8, 11),
        beforeLink: 'At the Center for Open Science (COS), we envision a future in which ideas, processes and ' +
            'outcomes of research are free and open to all. COS relies on contributions to build the free products you' +
            ' use and love. Help make the vision a reality with a ',
        linkText: 'gift today.',
        afterLink: '',
        background:'.donate-banner.week-5'
    }
];

function pickBanner(bannerOptions, date) {
    bannerOptions.sort(function (a, b) {
        return a.startDate - b.startDate;
    });

    var i;
    for (i = 0; i < bannerOptions.length; i++) {
        if (bannerOptions[i].startDate <= date && bannerOptions[i].endDate > date)
            return i;
    }
    return -1;
}

bannerPicked = pickBanner(bannerOptions, currentDate);

var Banner = {
    view: function(ctrl) {
        if (bannerPicked === -1) {
            return m('');
        }
        return m('.p-v-sm',
            m('.row',
                [
                    m('.col-md-12.m-v-sm',
                            m('div.conference-centering',
                                m('p', bannerOptions[bannerPicked].beforeLink,
                                    m('a.donate-text', { href:'https://cos.io/donate', onclick: function() {
                                        $osf.trackClick('link', 'click', 'DonateBanner - Donate now');
                                    }}, bannerOptions[bannerPicked].linkText), bannerOptions[bannerPicked].afterLink)
                            )
                    )
                ]
            )
        );
    }
};


var background = '.hidden';

if (bannerPicked > -1) {
    background = bannerOptions[bannerPicked].background;
}

module.exports = {
    Banner: Banner,
    background: background,
    pickBanner: pickBanner
};
