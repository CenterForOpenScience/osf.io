    $(document).ready(function() {
(function ($) {
    "use strict";

    var AwardBadge = function (options) {
      this.badges = options.badges;
        this.init('awardbadge', options, AwardBadge.defaults);
    };

    //inherit from Abstract input
    $.fn.editableutils.inherit(AwardBadge, $.fn.editabletypes.abstractinput);

    $.extend(AwardBadge.prototype, {
        /**
        Renders input from tpl

        @method render()
        **/
        render: function() {
          this.$input = this.$tpl.find('input');
          this.$list = this.$tpl.find('select');

          this.$list.empty();

          var fillItems = function ($el, data) {
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

        /**
        Gets value from element's html

        @method html2value(html)
        **/
        html2value: function(html) {
          /*
            you may write parsing method to get value by element's html
            e.g. "Moscow, st. Lenina, bld. 15" => {city: "Moscow", street: "Lenina", building: "15"}
            but for complex structures it's not recommended.
            Better set value directly via javascript, e.g.
            editable({
                value: {
                    city: "Moscow",
                    street: "Lenina",
                    building: "15"
                }
            });
          */
          return null;
        },

       /**
        Converts value to string.
        It is used in internal comparing (not for sending to server).

        @method value2str(value)
       **/
       value2str: function(value) {
           var str = '';
           if(value) {
               for(var k in value) {
                   str = str + k + ':' + value[k] + ';';
               }
           }
           return str;
       },

       /*
        Converts string to value. Used for reading value from 'data-value' attribute.

        @method str2value(str)
       */
       str2value: function(str) {
           /*
           this is mainly for parsing value defined in data-value attribute.
           If you will always set value by javascript, no need to overwrite it
           */
           return str;
       },

       /**
        Sets value of input.

        @method value2input(value)
        @param {mixed} value
       **/
       value2input: function(value) {
           if(!value) {
             return;
           }
           this.$input.filter('[name="badgeid"]').val(value.badgeid);
           this.$input.filter('[name="evidence"]').val(value.evidence);
       },

       /**
        Returns value of input.

        @method input2value()
       **/
       input2value: function() {
           return {
              badgeid: this.$list.filter('[name="badgeid"]').val(),
              evidence: this.$input.filter('[name="evidence"]').val(),
           };
       },

        /**
        Activates input: sets focus on the first field.

        @method activate()
       **/
       activate: function() {
            this.$input.filter('[name="badgeid"]').focus();
       },

       /**
        Attaches handler to submit form in case of 'showbuttons=false' mode

        @method autosubmit()
       **/
       autosubmit: function() {
           this.$input.keydown(function (e) {
                if (e.which === 13) {
                    $(this).closest('form').submit();
                }
           });
       }
    });

    AwardBadge.defaults = $.extend({}, $.fn.editabletypes.abstractinput.defaults, {
        tpl: '<div class="editable-address"><label><select name="badgeid" class="form-control input-sm"></select></label></div>'+
             '<div class="editable-address"><label><input type="url" name="evidence" class="form-control input-sm" placeholder="Evidence (Optional)"></label></div>',

        inputclass: '',
        badges: []
    });

    $.fn.editabletypes.AwardBadge = AwardBadge;

}(window.jQuery));
});
