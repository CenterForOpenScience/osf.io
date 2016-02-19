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
    }
    // Toggle individual view when clicked on header
    $('.support-head').click(function(){
        var item = $(this).parent();
        _toggleItem(item, item.hasClass('open'));
    });

    $('.expand-all').click(function(){
        $('.support-item').each(function(){
            _toggleItem($(this));
        });
    });

    $('.collapse-all').click(function(){
        $('.support-item').each(function(){
            _toggleItem($(this), true);
        });
    });

    $('.support-filter').keyup(function(){
        var text = $(this).val().toLowerCase();
        if (text.length < 2) {
            resetFilter();
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



});
