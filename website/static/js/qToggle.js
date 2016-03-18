/**
* Quick toggle plugin to toggle visibility of elements within the page by defining a trigger and a target
*
* Usage:
*     $(document).ready(function(){
*         $('.my-item').qToggle({'animation' : 'fade', animationOptions : { duration : 200 }});
*     });
*/
var $ = require('jquery');

// Create the defaults once
var pluginName = 'qToggle';
var defaults = {
    animation : '',
    animationOptions : {}
};

function qToggle (element, options) {
    var self = this;
    self.element = element;
    self.$el = $(element);
    self.settings = $.extend( {}, defaults, options );
    self._name = pluginName;

    self.targetID = self.$el.attr('data-qtoggle-target');
    self.groupID = self.$el.attr('data-qtoggle-group');
    self.toggleType = self.settings.animation ? self.settings.animation + 'Toggle' : 'toggle';
    if(self.targetID){
        self.$target = $(self.targetID);
        self.init();
    } else {
        console.warn('qtoggle needs a target to be defined by adding data-qtoggle-target to the trigger element for the  following item :', self.$el);
    }
}

qToggle.prototype.init = function () {
    var self = this;
    // set listener for the trigger
    self.$el.on('click', function(){
        if(self.toggleType !== 'toggle'){
            self.$target[self.toggleType](self.settings.animationOptions);
        } else {
            self.$target[self.toggleType]();
        }
        self.$el.toggleClass('active');

        // if part of group turn off other group items
        if(self.groupID){
            $('[data-qtoggle-group= \'' + self.groupID + '\']').each(function(){
                var item = $(this);
                var targetID = item.attr('data-qtoggle-target');
                if(targetID === self.targetID){ return; }
                if(self.toggleType !== 'toggle'){
                    $(targetID + ':visible')[self.toggleType](self.settings.animationOptions);
                } else {
                    $(targetID + ':visible')[self.toggleType]();
                }
                item.removeClass('active');
            });
        }

    });

};

$.fn.qToggle = function ( options ) {
    return this.each(function() {
        if ( !$.data( this, 'plugin_' + pluginName ) ) {
                $.data( this, 'plugin_' + pluginName, new qToggle( this, options ) );
        }
    });
};
