/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var donateBanner = require('js/home-page/donateBannerPlugin');



describe('donateBanner', () => {
    describe('pickBanner', () => {
        it('check picks correct data on startDate', () => {

            var bannerOptions = [
                {
                    startDate: new Date('August 16, 2017'),
                    endDate: new Date('August 23, 2017')
                }, {
                    startDate: new Date('August 9, 2017'),
                    endDate: new Date('August 16, 2017')
                }, {
                    startDate: new Date('August 23, 2017'),
                    endDate: new Date('August 30, 2017')
                },
            ];

           assert.equal(donateBanner.pickBanner(bannerOptions, new Date('August 9, 2017')), 0);
           assert.equal(donateBanner.pickBanner(bannerOptions, new Date('August 16, 2017')), 1);
           assert.equal(donateBanner.pickBanner(bannerOptions, new Date('August 26, 2017')), 2);
           assert.equal(donateBanner.pickBanner(bannerOptions, new Date('August 6, 2017')), -1);

        });
    });
});