
/**
* A simple UI component to use with divs that need to be collapsed or expanded.
*
* Usage:
*
*     $('#myPicker').osfToggleHeight({
*         height: 100, // the height that will be visible when collapsed
*         iconDown: 'fa fa-angle-down', // icon classes for the Down icon
*         iconUp : 'fa fa-angle-up' // icon classes for the Up icon
*     });
*/

'use strict';
var $ = require('jquery');

// Create the defaults once
var pluginName = 'osfToggleHeight';
var defaults = {
    height:  75,
    iconDown : 'fa fa-angle-down',
    iconUp : 'fa fa-angle-up'
};

// The actual plugin constructor
function ToggleHeight ( element, options ) {
    var self = this;
    self.element = element;
    self.$el = $(element);
    self.settings = $.extend( {}, defaults, options );
    self._defaults = defaults;
    self._name = pluginName;
    self.init();
}

ToggleHeight.prototype.init =  function () {
    var self = this;
    self.collapsed = true;
    self.showToggle = false;
    self.gradientDiv = $('<div class="toggle-height-gradient" style="display:none"></div>').appendTo(self.element);
    self.toggleDiv = $('<div class="toggle-height-toggle text-center" style="display:none"></div>').insertAfter(self.element);
    self.toggleDiv.click(self.toggle.bind(this));
    self.checkCollapse();
    $(window).resize(self.checkCollapse.bind(this));
};

ToggleHeight.prototype.removeToggle = function () {
    var self = this;
    self.$el.css('height', 'auto');
    self.gradientDiv.hide();
    self.toggleDiv.hide();
    self.showToggle = false;
    self.$el.removeClass('toggle-height-parent');
};

ToggleHeight.prototype.collapse = function () {
    var self = this;
    self.$el.css('height', self.settings.height + 'px');
    self.gradientDiv.show();
    self.toggleDiv.html('<i class="' + self.settings.iconDown +'"></i>').show();
};

ToggleHeight.prototype.expand = function (){
    var self = this;
    self.$el.css('height', 'auto');
    self.gradientDiv.hide();
    self.toggleDiv.html('<i class="' + self.settings.iconUp + '"></i>').show();
};

ToggleHeight.prototype.checkCollapse = function () {
    var self = this;
    if (self.element.scrollHeight <= self.settings.height){
        self.removeToggle();
    } else if (!self.showToggle){
        self.showToggle = true;
        self.$el.addClass('toggle-height-parent');
        if (self.collapsed){
            this.collapse();
        } else {
            self.expand();
        }
    }
};

ToggleHeight.prototype.toggle = function () {
    var self = this;
    if (self.collapsed) {
        self.expand();
    } else {
        self.collapse();
    }
    self.collapsed = !self.collapsed;
};


$.fn.osfToggleHeight = function ( options ) {
    return this.each(function() {
        if ( !$.data( this, 'plugin_' + pluginName ) ) {
                $.data( this, 'plugin_' + pluginName, new ToggleHeight( this, options ) );
        }
    });
};

module.exports = ToggleHeight;