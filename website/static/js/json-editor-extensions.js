var $ = require('jquery');

var jedit = require('json-editor'); // TODO webpackify


JSONEditor.defaults.editors.commentableString = JSONEditor.defaults.editors.string.extend({
	build: function() {
		var self = this;
        this._super();

		this.comment = $( "<span>Comments:</span><input type='text' class='form-control comment-input' placeholder='Comments or questions...'></input><button style='padding: 5px; margin-top:15px;' onclick='this.addComment' class='btn btn-primary btn-xs comment-button' id='comment' >New comment</button>")
		console.log(this.comment[2]);
		
		$(this.input).after(this.comment);
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
