var $ = require('jquery');
require('js/registrationEditor');
var jedit = require('json-editor');


JSONEditor.defaults.editors.commentableString = JSONEditor.defaults.editors.string.extend({
	build: function() {
		var self = this;
        this._super();

		this.comment = $( "<span class='comment-span'>Comments:</span><input type='text' class='form-control comment-input' placeholder='Comments or questions...'></input>");
		this.button = $("<button style='padding: 5px; margin-top:15px;' class='btn btn-primary btn-xs comment-button' id='comment'>Add comment</button>");

		$(this.button).click(function() {
			$(this).prev().after("<input type='text' class='form-control comment-input' placeholder='Comments or questions...'></input>");
		});

		$(this.input).after(this.comment);
		$(this.comment[1]).after(this.button);
		
	},
    getValue: function() {
		if(this.comment) {
			val = {
				"value": this._super(),
				"comments": this.comment[1].value
			}
			return val;
		}
		else {
			return this._super();
		}
	}
	
});
