var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/donate-banner.css');
require('css/meetings-and-conferences.css');

var currentDate = new Date();

var bannerOptions = [
    {
        startDate: new Date(2017, 10, 19),
        endDate: new Date(2017, 10, 28),
        imageLg: {
            src:'/static/img/front-page/giving_tuesday_week01.png',
            alt:'Things to look forward to: Thanksgiving Thursday, Black Friday, Cyber Monday, AND Giving Tuesday on ' +
            'Tuesday, November 28th. Please make a gift to support the OSF tools you use and love.'
        },
        imageSm: {
            src:'/static/img/front-page/giving_tuesday_week01_mobile.png',
            alt:'Giving Tuesday is coming on Tuesday, November 28th. Please make a gift to support the OSF tools you ' +
            'use and love.'
        },
    }, {
        startDate: new Date(2017, 10, 28),
        endDate: new Date(2017, 10, 29),
        imageLg: {
            src:'/static/img/front-page/giving_tuesday_week02.png',
            alt:'Happy Giving Tuesday! Please make a gift to support the OSF tools you use and love.'
        },
        imageSm: {
            src:'/static/img/front-page/giving_tuesday_week02_mobile.png',
            alt:'Happy Giving Tuesday! Please make a gift to support the OSF tools you use and love.'
        },
    }, {
        startDate: new Date(2017, 10, 29),
        endDate: new Date(2017, 11, 6),
        license: '© Nestlé',
        imageLg: {
            src:'/static/img/front-page/week03_dec2017.svg',
            alt:'The Center for Open Science created the OSF and a suite of free products to advance the work of the ' +
            'research community. If you value these tools, please make a gift to support COS’s efforts to improve and ' +
            'scale these services. DONATE NOW!'
        },
        imageSm: {
            src:'/static/img/front-page/week03_dec2017_mobile.svg',
            alt:'Support COS’s efforts to improve free products and advance the work of the research community.'
        },
    },
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
        var currentBanner = bannerOptions[bannerPicked];
        return m('.row',
                [
                    m('a', {href: 'https://www.crowdrise.com/centerforopenscience', onclick: function() {
                        $osf.trackClick('link', 'click', 'DonateBanner - Donate now');
                    }},
                        m('.col-sm-md-lg-12.hidden-xs',
                            m('img.donate-banner.img-responsive', currentBanner.imageLg)
                        ),
                        m('.col-xs-12.hidden-sm.hidden-md.hidden-lg',
                            m('img.donate-banner.img-responsive', currentBanner.imageSm)
                        )
                    ),
                ]
        );
    }
};

var background = '.donate-banner-background';

module.exports = {
    Banner: Banner,
    background: background,
    pickBanner: pickBanner
};
