/**
 * Adds a lovely dropdown menu to the green award button
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery'], factory);
    } else if (typeof $script === 'function') {
        global.attachDropDown  = factory(jQuery);
        $script.done('awarder');
    }else {
        global.attachDropDown  = factory(jQuery);
    }
}(this, function($) {
    'use strict';

    var AwardBadge = function(options) {
        this.badges = options.badges;
        this.init('awardbadge', options, AwardBadge.defaults);
    };

    //inherit from Abstract input
    $.fn.editableutils.inherit(AwardBadge, $.fn.editabletypes.abstractinput);

    $.extend(AwardBadge.prototype, {
        render: function() {
            this.$input = this.$tpl.find('input');
            this.$list = this.$tpl.find('select');

            this.$list.empty();

            var fillItems = function($el, data) {
                if ($.isArray(data)) {
                    for (var i = 0; i < data.length; i++) {
                        if (data[i].children) {
                            $el.append(fillItems($('<optgroup>', {
                                label: data[i].text
                            }), data[i].children));
                        } else {
                            $el.append($('<option>', {
                                value: data[i].value
                            }).text(data[i].text));
                        }
                    }
                }
                return $el;
            };

            fillItems(this.$list, this.badges);
        },

        html2value: function(html) {
            return null;
        },

        value2str: function(value) {
            var str = '';
            if (value) {
                for (var k in value) {
                    str = str + k + ':' + value[k] + ';';
                }
            }
            return str;
        },

        str2value: function(str) {
            return str;
        },

        value2input: function(value) {
            if (!value) {
                return;
            }
            this.$input.filter('[name="badgeid"]').val(value.badgeid);
            this.$input.filter('[name="evidence"]').val(value.evidence);
        },

        input2value: function() {
            return {
                badgeid: this.$list.filter('[name="badgeid"]').val(),
                evidence: this.$input.filter('[name="evidence"]').val(),
            };
        },

        activate: function() {
            this.$input.filter('[name="badgeid"]').focus();
        },

        autosubmit: function() {
            this.$input.keydown(function(e) {
                if (e.which === 13) {
                    $(this).closest('form').submit();
                }
            });
        }
    });

    AwardBadge.defaults = $.extend({}, $.fn.editabletypes.abstractinput.defaults, {
        tpl: '<div class="editable-address"><label><select name="badgeid" class="form-control input-sm"></select></label></div>' +
        '<div class="editable-address"><label>' +
        '<input type="url" name="evidence" class="form-control input-sm" placeholder="Evidence (Optional)"></label></div>',
        inputclass: '',
        badges: []
    });

    $.fn.editabletypes.AwardBadge = AwardBadge;

    function attachDropDown (url) {
        $.ajax({
            method: 'GET',
            url: url
        }).done(function(ret) {
            $('#awardBadge').editable({
                name: 'title',
                title: 'Award Badge',
                display: false,
                highlight: false,
                placement: 'bottom',
                showbuttons: 'bottom',
                type: 'AwardBadge',
                value: ret[0],
                badges: ret,
                ajaxOptions: {
                    type: 'POST',
                    dataType: 'json',
                    contentType: 'application/json'
                },
                url: nodeApiUrl + 'badges/award/',
                params: function(params) {
                    // Send JSON data
                    return JSON.stringify(params.value);
                },
                success: function(data) {
                    document.location.reload(true);
                },
                pk: 'newBadge'
            });
        }).fail(
            $.osf.handleJSONError
        );
    };

    return attachDropDown;

}));

//userApiUrl + 'badges/json/'
