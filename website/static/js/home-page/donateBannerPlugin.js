var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/donate-banner.css');
require('css/meetings-and-conferences.css');

var currentDate = new Date();

var bannerOptions = [
    {
        startDate: new Date(2017, 10, 29),
        endDate: new Date(2017, 11, 6),
        imageLg: {
            src:'/static/img/front-page/week03_dec2017.svg',
            alt:'The Center for Open Science created the OSF and a suite of free products to advance the work of the ' +
            'research community. If you value these tools, please make a gift to support COS’s efforts to improve and ' +
            'scale these services. DONATE NOW! Image © Nestlé'
        },
        imageSm: {
            src:'/static/img/front-page/week03_dec2017_mobile.svg',
            alt:'Support COS’s efforts to improve free products and advance the work of the research community. ' +
            'Image © Nestlé'
        },
    }, {
        startDate: new Date(2017, 11, 6),
        endDate: new Date(2017, 11, 13),
        imageLg: {
            src:'/static/img/front-page/week04_dec2017.svg',
            alt:'Thousands of researchers use the OSF and its related services daily. If you value the OSF, make a ' +
            'donation to support the Center for Open Science and its ongoing efforts to improve and advance these ' +
            'public goods. Image © Pressmaster/Shutterstock'
        },
        imageSm: {
            src:'/static/img/front-page/week04_dec2017_mobile.svg',
            alt:'Thousands of researchers use the OSF and its related services. Make a donation to support these ' +
            'ongoing efforts. Image © Pressmaster/Shutterstock'
        },
    }, {
        startDate: new Date(2017, 11, 13),
        endDate: new Date(2017, 11, 20),
        imageLg: {
            src:'/static/img/front-page/week05_dec2017.svg',
            alt:'The Center for Open Science created the OSF and its related services as public goods. While these ' +
            'services will always be free to use, they are not free to build, maintain, and improve. Please support the' +
            ' OSF and COS with a donation today. Image © joker1991/Shutterstock'
        },
        imageSm: {
            src:'/static/img/front-page/week05_dec2017_mobile.svg',
            alt:'The OSF will always be free to use, but it is not free to build, maintain, and improve. Give a gift' +
            ' today. Image © joker1991/Shutterstock'
        },
    }, {
        startDate: new Date(2017, 11, 20),
        endDate: new Date(2017, 11, 27),
        imageLg: {
            src:'/static/img/front-page/week06_dec2017.svg',
            alt: 'The Center for Open Science launched the OSF with the goal of creating a service to support the ' +
            'entire research cycle and remove barriers to accessing data. Support COS’s efforts to advance the work of' +
            ' researchers with a gift today! Image © angellodeco/Shutterstock'
        },
        imageSm: {
            src:'/static/img/front-page/week06_dec2017_mobile.svg',
            alt:'Support COS’s mission to create a service to support the entire research cycle. Image © ' +
            'angellodeco/Shutterstock'
        },
    }, {
        startDate: new Date(2017, 11, 27),
        endDate: new Date(2018, 0, 4),
        imageLg: {
            src: '/static/img/front-page/week07_dec2017.svg',
            alt: 'At the Center for Open Science, we envision a future in which ideas, processes, and outcomes of ' +
            'research are free and open. COS relies on contributions to build the free products you use and love. Help' +
            ' make our vision a reality with a gift today. Image © Smithsonian Institution Archives'
        },
        imageSm: {
            src: '/static/img/front-page/week07_dec2017_mobile.svg',
            alt: 'Make a contribution to COS to build the free products you use and love. Image © Smithsonian ' +
            'Institution Archives'
        },
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
