import Ember from 'ember';
import config from './config/environment';

var Router = Ember.Router.extend({
  location: config.locationType
});


Router.map(function() {
  this.route('dashboard', { path: '/spa' });
  this.route('profile', { path: '/profile' });
  this.route('logout', { path: '/logout' });
  this.route('reset-password', { path: '/reset-password' });
});

export default Router;
