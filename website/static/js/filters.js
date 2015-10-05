(function($){
    $.fn.filters = function (options) {
        var settings = $.extend({
            items: '.items'
        }, options);

        var filterConstraints = {};
        var searchConstraints = {};

        var search = function(el) {
            var content, exists;
            for (key in searchConstraints) {
                content = jQuery(el.querySelector(key)).text().toLowerCase();
                exists = content.indexOf(searchConstraints[key]);
                if (exists == -1) {
                    return false;
                }
            }
            return true;
        };

        var filter = function(el) {
            var content, type, selector, match;
            for (key in filterConstraints) {
                selector = settings.groups[key]['filter'];
                type = settings.groups[key]['type'];
                match = filterConstraints[key];
                if (type === "text") {
                    content = jQuery(el.querySelector(selector)).text();
                    if (match.indexOf(content) == -1) {
                        return false;
                    }
                }
                else if (type === "checkbox") {
                    if (match.indexOf(el.querySelector(selector).checked) == -1) {
                        return false;
                    }
                }
            }
            return true;
        };

        var toggle = function() {
            var activeItems = $(settings.items);
            $(settings.items).each(function() {
                if (!search(this)) {
                    activeItems.splice(activeItems.index(this), 1);
                    $(this).fadeOut();
                }
                else if (!filter(this)){
                    activeItems.splice(activeItems.index(this), 1);
                    $(this).fadeOut();
                }
            });
            $(activeItems).fadeIn();
            if (settings.callback !== undefined) {
                settings.callback(activeItems.length < $(settings.items).length, activeItems.length == 0)
            }
        };

        for (key in settings.groups) {
            for (key in settings.groups[key].buttons) {
                $('#' + key).on('click', function() {
                    $(this).toggleClass('btn-primary btn-default');
                    var group = this.parentElement.parentElement.id;
                    var match = settings.groups[group].buttons[this.id];
                    try {
                        var index = filterConstraints[group].indexOf(match);
                        if (index == -1) {
                            filterConstraints[group].push(match);
                        }
                        else {
                            filterConstraints[group].splice(index, 1);
                            if (filterConstraints[group].length == 0) {
                                delete filterConstraints[group];
                            }
                        }
                    }
                    catch(TypeError) {
                        filterConstraints[group] = [match];
                    }
                    toggle();
                });
            }
        }

        for (key in settings.inputs) {
            jQuery('#' + key).keyup(function() {
                var selector = settings.inputs[this.id];
                var text = $(this).val().toLowerCase();
                searchConstraints[selector] = text;
                toggle();
            });
        }
    }
}(jQuery));
