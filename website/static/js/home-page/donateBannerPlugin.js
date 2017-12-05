var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/donate-banner.css');
require('css/meetings-and-conferences.css');


var DonateBanner = {
    controller: function() {
        var self = this;
        self.banner = m.prop();
        self.bannerLoaded = m.prop(false);

        // Load new and noteworthy nodes
        var bannerUrl = $osf.apiV2Url('banners/current');
        var bannerPromise = m.request({method: 'GET', url: bannerUrl}, background=true);
        bannerPromise.then(function(result){
            self.banner(result.data);
            self.bannerLoaded(true);
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
        var default_photo = args.banner.attributes.default_photo_url;
        var mobile_photo = args.banner.attributes.mobile_photo_url;
        var default_text = args.banner.attributes.default_text;
        var mobile_text = args.banner.attributes.mobile_text;
        var color = args.banner.attributes.color;

        document.documentElement.style.setProperty('--banner-color', color);

        return m('.row',
            [
                m('a', {
                        href: 'https://www.crowdrise.com/centerforopenscience', onclick: function () {
                            $osf.trackClick('link', 'click', 'DonateBanner - Donate now');
                        }
                    },
                    m('.col-sm-md-lg-12.hidden-xs',
                        m('img.donate-banner.img-responsive', {'src': default_photo, 'alt': default_text})
                    ),
                    m('.col-xs-12.hidden-sm.hidden-md.hidden-lg',
                        m('img.donate-banner.img-responsive', {'src': mobile_photo, 'alt': mobile_text})
                    )
                ),
            ]
        );
    }
};

module.exports = DonateBanner;