import Ember from 'ember';
import config from './config/environment';

const Router = Ember.Router.extend({
    location: config.locationType
});

Router.map(function() {
    this.route('ember-sample');
    this.route('file-detail', function() {
        this.route('revisions');
    });
});

export default Router;
