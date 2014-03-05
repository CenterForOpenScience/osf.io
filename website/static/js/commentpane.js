(function(window, document, $) {

    'use strict';

    var defaults = {
        animateTime: 100,
        minViewWidth: 150,
        toggleWidth: 1/3,
        maxWidthProp: 2/3
    };

    var CommentPane = CommentPane || function(selector, options) {

        var $pane = $(selector);
        var $handle = $pane.find('.cp-handle');
        var $sidebar = $pane.find('.cp-sidebar');
        var $bar = $pane.find('.cp-bar');
        var $toggleElm = $.merge($pane, $sidebar);

        options = $.extend({}, defaults, options);
        if (options.maxWidthProp < options.toggleWidth) {
            throw(
                'Option `toggleWidth` must be greater than or equal to ' +
                'option `maxWidthProp`.'
            );
        }

        var makeAllElementsUnselectable = function(){
            $(document).children().each(function (index, elm) {
                $(elm).addClass('unselectable');
            });
        };

        var makeAllElementsSelectable = function(){
            $(document).children().each(function (index, elm) {
                $(elm).removeClass('unselectable');
            });
        };

        var maxWidth = function(targetWidth) {
            var bodyWidth = $(document.body).width();
            return Math.min(targetWidth, bodyWidth * options.maxWidthProp);
        };

        var toggle = function() {
            var width;
            if ($pane.width()) {
                width = 0;
            } else {
                var bodyWidth = $(document.body).width();
                width = options.toggleWidth * bodyWidth;
            }
            $toggleElm.animate(
                {width: width},
                options.animateTime
            );
        };

        var init = function(){

            $bar.on('mousedown', function() {
                makeAllElementsUnselectable();
                $(document).on('mousemove', function(event) {
                    var bodyWidth = $(document.body).width();
                    var dragWidth = document.body.clientWidth - event.pageX;
                    var width = maxWidth(dragWidth) + 'px';
                    $pane.css('width', width);
                    $('.cp-sidebar').css('width', width);
                });
                $(document).on('mouseup', function(){
                    $(document).off('mousemove');
                    $(document).off('mouseup');
                    makeAllElementsSelectable();
                    if ($pane.width() < options.minViewWidth) {
                        $pane.animate(
                            {width: '0'}, options.animateTime
                        );
                    }
                })
            });

            $(window).on('resize', function() {
                var bodyWidth = $(document.body).width();

            });

            $handle.on('click', toggle);

        };

        init();

    };

    if ((typeof module !== 'undefined') && module.exports) {
        module.exports = CommentPane;
    }
    if (typeof ender === 'undefined') {
        this.CommentPane = CommentPane;
    }
    if ((typeof define === 'function') && define.amd) {
        define('commentpane', [], function() {
            return CommentPane;
        });
    }

}).call(this, window, document, $);
