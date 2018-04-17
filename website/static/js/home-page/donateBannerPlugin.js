var m = require('mithril');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var lodashGet = require('lodash.get');

require('css/donate-banner.css');

var DonateBanner = {
    controller: function() {
        var self = this;
        self.banner = m.prop();
        self.bannerLoaded = m.prop(false);

        // Load banner
        var domain = lodashGet(window, 'contextVars.apiV2Domain', '');
        var bannerUrl =   domain + '_/banners/current/';
        var bannerPromise = m.request({method: 'GET', url: bannerUrl}, background=true);
        bannerPromise.then(function(result){
            self.banner(result.data);
            self.bannerLoaded(true);
        }, function(error) {
            Raven.captureMessage('Error in request to ' + bannerUrl, {
                extra: {error: error}
            });
        });
    },
    view : function(ctrl) {

        function bannerTemplate () {
            return m.component(BannerDisplay, {
                banner : ctrl.banner(),
            });
        }

        if (ctrl.bannerLoaded()) {
            return ctrl.banner().attributes.start_date ? m('', [bannerTemplate()]):  m('');
        }

        return m('');
    }
};


var BannerDisplay = {
    view: function(ctrl, args) {
        var defaultPhoto = args.banner.links.default_photo;
        var mobilePhoto = args.banner.links.mobile_photo;
        var defaultAltText = args.banner.attributes.default_alt_text;
        var mobileAltText = args.banner.attributes.mobile_alt_text;
        var color = args.banner.attributes.color;
        var link = args.banner.attributes.link;
        var name = args.banner.attributes.name;

        $('.donate-banner-background')[0].style.backgroundColor = color;

        return m('.row',
            [
                m('a', {
                        href: link,
                        onclick: function () {
                            $osf.trackClick('link', 'click', 'Banner - ' + name);
                          },
                        target : '_blank'
                    },
                    m('.col-sm-md-lg-12.hidden-xs',
                        m('img.donate-banner.img-responsive.banner-image', {'src': defaultPhoto, 'alt': defaultAltText})
                    ),
                    m('.col-xs-12.hidden-sm.hidden-md.hidden-lg',
                        m('img.donate-banner.img-responsive.banner-image', {'src': mobilePhoto, 'alt': mobileAltText})
                    )
                ),
            ]
        );
    }
};

module.exports = DonateBanner;
