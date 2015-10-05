$(document).ready(function() {
     window.cancelProp = function(e) {
        e.cancelBubble = true;
        if (e.stopPropagation) {
            e.stopPropagation();
        }
    };

    window.toggleIcon = function(el) {
        jQuery(el.querySelector(".toggle-icon")).toggleClass("fa-angle-down fa-angle-up");
    };
});

