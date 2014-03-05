(function(win, doc) {
    'use strict';
    var CommentPane = CommentPane || function(selector){
        var main = this,
        el = $(selector),
        state = 'closed',
        makeAllElementsUnselectable = function(){
            $(document).children().each(function (index, el){
                $(el).addClass('unselectable');
            });
        },
        makeAllElementsSelectable = function(){
            $(document).children().each(function (index, el){
                $(el).removeClass('unselectable');
            });
        },
        init = function(){
//            $('.cp-handle').on('click', function(){
//                var handle = $(this);
//                main.toggle();
//            });

            $( ".cp-handle" ).on('mousedown', function(event){
                var downevent = event;
                makeAllElementsUnselectable();
                $(document).on('mousemove', function(event){
                    el.css('width', (document.body.clientWidth-event.pageX-downevent.offsetX) + 'px');
                    $('.cp-sidebar').css('width', (document.body.clientWidth-event.pageX-downevent.offsetX) + 'px');
                });
                $(document).on('mouseup', function(){
                    $(document).off('mousemove');
                    $(document).off('mouseup');
                    makeAllElementsSelectable();
                    if(el.width() < 100){
                        el.animate(
                            { width: "0px"}, 100, function(){}
                        );
                    }
                })
            });

            $( ".cp-bar" ).on('mousedown', function(){
                makeAllElementsUnselectable();
                $(document).on('mousemove', function(event){
                    el.css('width', (document.body.clientWidth-event.pageX) + 'px');
                    $('.cp-sidebar').css('width', (document.body.clientWidth-event.pageX) + 'px');
                });
                $(document).on('mouseup', function(){
                    $(document).off('mousemove');
                    $(document).off('mouseup');
                    makeAllElementsSelectable();
                    if(el.width() < 100){
                        el.animate(
                            { width: "0px"}, 100, function(){}
                        );
                    }
                })
            });
        };
        init();

//        this.toggle = function(){
//            if(state == 'closed'){
//                el.animate(
//                    {width:"300"}, 100, function(){}
//                );
//                state = 'opened';
//            }else{
//                el.animate(
//                    {right:-el.width()}, 100, function(){
//                    }
//                );
//                state = 'closed';
//            }
//        };
    };
    if ((typeof module !== 'undefined') && module.exports) {
        module.exports = CommentPane;
    }
    if (typeof ender === 'undefined') {
        this.CommentPane = CommentPane;
    }
    if ((typeof define === "function") && define.amd) {
        define("commentpane", [], function() {
            return CommentPane;
        });
    }
}).call(this, window, document);

$(document).ready(function(){
    $(document.body).append(
          '<div id="commentpane">'
        + '    <div class="cp-handle"></div>'
        + '    <div class="cp-bar"></div>'
        + '    <div class="cp-sidebar">'
        + '        <p>Lorem ipsum</p>'
        + '    </div>'
        + '</div>'
    );
    var Comments = new CommentPane('#commentpane');
});