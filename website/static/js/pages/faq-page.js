/**
 * Code for interaction in the support page
 */

'use strict';
var $ = require('jquery');

$(document).ready(function(){
    /**
     * handle expanding or collapsing individual support item with jQuery
     * @param item {Object} jQuery object for the .support-item element
     * @param turnOff {Boolean} true if we are closing and open item
     * @private
     */
    function changeExpandState (item, turnOff) {
        var body = item.children('.support-body');
        var head = item.children('.support-head');
        var icon = head.children('.fa');
        if (turnOff){
            body.slideUp(200);
            icon.removeClass('fa-angle-down').addClass('fa-angle-right');
            item.removeClass('open').addClass('collapsed');
        } else {
            body.slideDown(200);
            icon.removeClass('fa-angle-right').addClass('fa-angle-down');
            item.removeClass('collapsed').addClass('open');
        }
    }

    /**
     * Resets the filter states for searching support items
     */
    function resetFilter (noCollapse) {
        if(!noCollapse){
            $('.support-item').each(function() {
                var $el = $(this);
                changeExpandState($el, true);
                $el.removeClass('support-nomatch');
            });
        }
        $('.support-filter').val('');
        $('.clear-search').removeClass('clear-active');
        searchItemIndex = 0;

    }

    var searchItemIndex = 0; // Index for which search result is now supposed to be in view; for prev and next buttons

    /**
     * Small utility function to ease scrolling into locations in the body
     * @param el {Object} jquery element object
     */
    function scrollTo (el) {
        var location = el ? el.offsetTop : 150; // Scroll to top if nothing given
        $('html, body').animate({
            scrollTop: location-150
        }, 500);
    }


    /**
     * Affix or restore search layer based on location
     */
    function fixSearchLayer () {
        var topOffset = $(window).scrollTop();
        var $searchLayer = $('.search-layer');
        if(topOffset > 100 && !$searchLayer.hasClass('fixed-layer')){
            $searchLayer.addClass('fixed-layer');
            $('.support-title').hide();
            $('.search-up').removeClass('disabled');
            $('.content-layer').addClass('content-padding'); // To avoid a suddent layout shift when affixing search layer
        }
        if(topOffset <= 100 && $searchLayer.hasClass('fixed-layer')){
            $searchLayer.removeClass('fixed-layer');
            $('.support-title').show();
            $('.search-up').addClass('disabled');
            $('.content-layer').removeClass('content-padding');
        }
    }

    /* expand or collapse on clicking support item header */
    $('.support-head').click(function(){
        var $item = $(this).parent();
        changeExpandState($item, $item.hasClass('open'));
    });

    /* Expand All button event  */
    $('.search-expand').click(function(){
        resetFilter(true);
        $('.support-item').each(function(){
            changeExpandState($(this));
        });
    });

    /* Collapse All button event  */
    $('.search-collapse').click(function(){
        resetFilter();
        $('.support-item').each(function(){
            changeExpandState($(this), true);
        });
    });

    /* Top button event to scroll to top*/
    $('.search-up').click(function(){
        scrollTo();
    });


    $('.clear-search').click(function(){
        resetFilter();
    });

    $('.support-filter').keyup(function(){
        var text = $(this).val().toLowerCase();
        if(text.length === 0){
            resetFilter();
            return;
        }
        $('.clear-search').addClass('clear-active');
        if (text.length < 2) {
            return;
        }
        var $el;
        var content;
        $('.support-item').each(function(){
            $el = $(this);
            content = $el.text().toLowerCase();
            if (content.indexOf(text) !== -1) {
                changeExpandState($el);
                $el.removeClass('support-nomatch');
            } else {
                changeExpandState($el, true);
                $el.addClass('support-nomatch');
            }
        });
    });

    // Handle fixing support search box on scroll
    $(window).scroll(fixSearchLayer);
    fixSearchLayer();
});