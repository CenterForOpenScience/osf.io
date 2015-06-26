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
    var $commentsList = $('<ul>', {
		'class': 'list-group'
	});
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
    
    self.$element = $('<li>', {
		'class': 'list-group-item'
	});
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
			//if(window.contextVars.currentUser === Comments.Comment.user) {
				self.editable = false;
				$(this).addClass('disabled');
				self.$input.addClass('disabled');
			// } else {
			// 	console.log('Only the author may edit this comment');
			// }
        }
    }));
	$control.append($('<a>', {
		'class': 'btn fa fa-pencil',
		click: function() {
			$(this).removeClass('disabled');
			self.$input.toggleClass('disabled');
			//if (window.contextVars.currentUser === this.comments.user) {
				console.log('u rite');
			//}
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
