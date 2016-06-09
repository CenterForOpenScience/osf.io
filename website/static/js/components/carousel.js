/**
 * Bootstrap carousel components.
 */
'use strict';
var $  = require('jquery');
var m = require('mithril');

// We need to use a CSS ID in order for the controls to work
var CAROUSEL_ID = '__carousel';


// TODO: Make these controls look better
var CarouselControls = {
    view: function() {
        return m('div', [
            m('a.left.carousel-control', {href: '#' + CAROUSEL_ID, 'data-slide': 'prev', style: {'padding-top': '5%', width: '5%', 'background-image': 'none'}}, '‹'),
            m('a.right.carousel-control', {href: '#' + CAROUSEL_ID, 'data-slide': 'next', style: {'padding-top': '5%', width: '5%', 'background-image': 'none'}}, '›')
        ]);
    }
};

var Carousel = {
    view: function(ctrl, opts, children) {
        opts = opts || {};
        var interval = opts.interval || null;
        function config(elem, isInitialized) {
            if (!isInitialized) {
                $(elem).carousel({interval: interval});
            }
        }
        opts = $.extend({}, {id: CAROUSEL_ID, config: config}, opts);
        return m('.carousel slide', opts, [
            m('.carousel-inner', {}, children),
            opts.controls ? m.component(CarouselControls, {}) : ''
        ]);
    }
};

var CarouselRow = {
    view: function(ctrl, opts, children) {
        return m('div', {className: 'item' + (opts.active ? ' active' : '')}, [
            m('.row', {style: {'text-align': 'center'}}, children)
        ]);
    }
};

module.exports = {
    CarouselControls: CarouselControls,
    Carousel: Carousel,
    CarouselRow: CarouselRow
};
