import Ember from 'ember';
import NodeActionsMixin from 'ember-osf/mixins/node-actions';

export default Ember.Controller.extend(NodeActionsMixin, {
    isAdmin: Ember.computed(function() {
        return this.get('model').get('currentUserPermissions').indexOf('admin') >= 0;
    }),
});
