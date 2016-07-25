import Ember from 'ember';
import NodeActionsMixin from 'ember-osf/mixins/node-actions';

export default Ember.Controller.extend(NodeActionsMixin, {
    isAdmin: Ember.computed(function() {
        return this.get('model').get('currentUserPermissions').indexOf('admin') >= 0;
    }),
    canEdit: Ember.computed('isAdmin', 'isRegistration', function() {
        return this.get('isAdmin') && !(this.get('model').get('registration'));
    }),
});
