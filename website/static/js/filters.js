(function($){
    $.fn.filters = function (options) {
        var settings = $.extend({
            items: '.items',
            buttonClass: '.filter-btn',
            inputClass: '.searchable',
            buttonGroupClass: '.filtergroup'
        }, options);

        var active = {};

        var search = function(el, constraints) {
            var content, exists;
            for (key in constraints) {
                content = jQuery(el.querySelector(key)).text().toLowerCase();
                exists = content.indexOf(constraints[key]);
                if (exists == -1) {
                    return false;
                }
            }
            return true;
        };
        var getSearchConstraints = function() {
            var inputs, selector, constraints, text;
            constraints = {};
            inputs = $(settings.inputClass);
            for (var i = 0; i < inputs.length; i++) {
                selector = $(inputs[i]).attr('search');
                text = $(inputs[i]).val().toLowerCase()
                constraints[selector] = text;
            }
            return constraints;
        };

        var filter = function(el, constraints) {
            var content;
            for (key in constraints) {
                content = jQuery(el.querySelector(key)).text();
                if (constraints[key].indexOf(content) == -1) {
                    return false;
                }
            }
            return true;
        };

        var getFilterConstraints = function() {
            var toggle, selector, text, constraints;
            constraints = {};
            for (key in active) {
                for (var j = 0; j < active[key].length; j++) {
                    toggle = active[key][j];
                    selector = $(toggle.parentElement).attr('filter');
                    text = $(toggle).attr('match');
                    if (constraints[selector] === undefined) {
                        constraints[selector] = [text];
                    } else {
                        constraints[selector].push(text);
                    }
                }
            }
            return constraints;
        };

        var toggle = function() {
            var activeItems = $(settings.items);
            var searchConstraints = getSearchConstraints();
            var filterConstraints = getFilterConstraints();
            $(settings.items).each(function() {
                if (!search(this, searchConstraints)) {
                    activeItems.splice(activeItems.index(this), 1);
                    $(this).fadeOut();
                }
                else if (!filter(this, filterConstraints)){
                    activeItems.splice(activeItems.index(this), 1);
                    $(this).fadeOut();
                }
            });
            $(activeItems).fadeIn();
            if (settings.callback !== undefined) {
                settings.callback(activeItems.length < $(settings.items).length, activeItems.length == 0)
            }
        };

        jQuery(settings.buttonClass).on('click', function () {
            var buttonGroup = this.parentElement.getAttribute('filter');
            $(this).toggleClass('btn-primary btn-default');
            if (active[buttonGroup] === undefined) {
                active[buttonGroup] = [this];
            } else if (active[buttonGroup].indexOf(this) == -1) {
                active[buttonGroup].push(this);
            } else {
                active[buttonGroup].splice(active[buttonGroup].indexOf(this), 1);
            }
            toggle();
        });

        return jQuery(settings.inputClass).keyup(function() {
            toggle();
        });
    }
}(jQuery));
