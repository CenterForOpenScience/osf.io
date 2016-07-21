import Ember from 'ember';

import markdown from 'npm:markdown';

var result = markdown.full.render('# markdown-it rulezz!');

export default Ember.Controller.extend({
    markdownText: result,
});
