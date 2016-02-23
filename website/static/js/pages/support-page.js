/**
 * Code for interaction in the support page
 */

'use strict';

var Raven = require('raven-js');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

$(document).ready(function(){
    /**
     * Toggle individual item with jQuery
     * @param item {Object} jQuery object for the .support-item element
     * @param turnOff {Boolean} true if we are closing and open item
     * @private
     */
    function _toggleItem (item, turnOff) {
        var body = item.children('.support-body');
        var head = item.children('.support-head');
        var icon = head.children('.fa');
        if (turnOff){
            body.slideUp();
            icon.removeClass('fa-angle-down').addClass('fa-angle-right');
            item.removeClass('open').addClass('collapsed');
        } else {
            body.slideDown();
            icon.removeClass('fa-angle-right').addClass('fa-angle-down');
            item.removeClass('collapsed').addClass('open');
        }


    }

    function resetFilter () {
        $('.support-item').each(function() {
            var el = $(this);
            _toggleItem(el, true);
            el.removeClass('support-nomatch');
        });
        $('.support-filter').val('');
        $('.clear-search').removeClass('clear-active');
    }

    var searchItemIndex = 0; // Index for which search result is now supposed to be in view; for prev and next buttons

    function scrollTo (el) {
        var location = el.offsetTop;
        $(window).scrollTop(location-150);
    }
    // Toggle individual view when clicked on header
    $('.support-head').click(function(){
        var item = $(this).parent();
        _toggleItem(item, item.hasClass('open'));
    });

    $('.search-expand').click(function(){
        $('.support-item').each(function(){
            _toggleItem($(this));
        });
    });

    $('.search-collapse').click(function(){
        $('.support-item').each(function(){
            _toggleItem($(this), true);
        });
    });

    $('.search-up').click(function(){
        $(window).scrollTop(0);
    });
    $('.search-previous').click(function(){
        if(searchItemIndex > 0){
            var openItems = $('.support-item.open');
            var prevEl = openItems.get(searchItemIndex-1);
            scrollTo(prevEl);
            $(prevEl).addClass('search-selected');
            $(openItems.get(searchItemIndex)).removeClass('search-selected');
            searchItemIndex--;
        }
    });
    $('.search-next').click(function(){
        var openItems = $('.support-item.open');
        var nextEl = openItems.get(searchItemIndex+1);
        if(nextEl){
            scrollTo(nextEl);
            $(nextEl).addClass('search-selected');
            $(openItems.get(searchItemIndex)).removeClass('search-selected');
            searchItemIndex++;
        }
    });


    $('.clear-search').click(resetFilter);

    $('.support-filter').keyup(function(){
        var text = $(this).val().toLowerCase();
        if(text.length === 0){
            resetFilter();
        }
        $('.clear-search').addClass('clear-active');
        if (text.length < 2) {
            return;
        }
        var el;
        var content;
        $('.support-item').each(function(){
            el = $(this);
            content = el.text().toLowerCase();
            if (content.indexOf(text) !== -1) {
                _toggleItem(el);
                el.removeClass('support-nomatch');
            } else {
                _toggleItem(el, true);
                el.addClass('support-nomatch');
            }
        });
    });

    function fixSearchLayer () {
        var topOffset = $(window).scrollTop();
        var searchLayer = $('.search-layer');
        if(topOffset > 100 && !searchLayer.hasClass('fixed-layer')){
            searchLayer.addClass('fixed-layer');
            $('.support-title').hide();
        }
        if(topOffset <= 100 && searchLayer.hasClass('fixed-layer')){
            searchLayer.removeClass('fixed-layer');
            $('.support-title').show();
        }
    }

    // Handle fixing support search box on scroll
    $(window).scroll(fixSearchLayer);
    fixSearchLayer();

});
