var $ = require('jquery');
require('js/registrationEditor');
var jedit = require('json-editor');

var curentUser = window.contextVars.currentUser || {
    pk: null,
    name: 'Anonymous'
};

var Comments = function($element){
    var self = this;

    self.comments = [];

    var $commentsDiv = $('<div>');
    var $commentsList = $('<ul>');
    self.$commentsList = $commentsList;    
    $commentsDiv.append($commentsList);
    $commentsDiv.append($('<button>', {
        'class': 'btn btn-primary btn-xs',
        html: 'Add comment',
        click: self.add.bind(self)
    }));
    $element.append($commentsDiv);
    
    self.add();
};
Comments.prototype.Comment = function(value){
    var self = this;

    value = value || '';

    self.user = {
        pk: curentUser.id,
        name: curentUser.fullname
    };

    self.editable = true;

    self.$input = $('<input>',
                    {
                        'class': 'form-control',
                        type: 'text',
                        placeholder: 'Comments or questions...',
                        html: value
                    }
                   );
    
    self.$element = $('<li>');
    var $row = $('<div>', {
        'class': 'row'
    });
    $row.append($('<div>', {
        'class': 'col-md-6'
    }).append(self.$input));
    var $control = $('<div>', {
        'class': 'col-md-3'
    });
    $control.append($('<a>', {
        'class': 'btn fa fa-check',
        click: function() {
            self.editable = false;
            $(this).addClass('disabled');
            self.$input.addClass('disabled');
        }
    }));
    $row.append($control);
    
    self.$element.append($row);
};
Comments.prototype.add = function() {
    var self = this;

    var comment = new self.Comment();
    self.comments.push(comment);
    self.$commentsList.append(comment.$element);
};

JSONEditor.defaults.editors.commentableString = JSONEditor.defaults.editors.string.extend({
    build: function() {
        var self = this;
        this._super();

        var $element = $('<div>');
        $(this.input).after($element);
        this.comments = new Comments($element);        
    },
    getValue: function() {
        if (this.comments) {
            var comments = $.map(this.comments.comments, function(comment) {
                return {
                    value: comment.$input.val(),
                    user: comment.user
                };
            });
            var val = {
                value: this._super(),
                comments: comments
            };
            return val;
        } else {
            return this._super();
        }
    }

});
