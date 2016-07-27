import Ember from 'ember';

import NodeActionsMixin from 'ember-osf/mixins/node-actions';

export default Ember.Controller.extend(NodeActionsMixin, {
    contributors: Ember.A(),

    isContributor: Ember.computed('user', 'contributors', function() {
        // Is a contributor if userId in list of known contributors
        return !!this.get('contributors').findBy('userId', this.get('user.id'));
    }),

    isAdmin: Ember.computed(function() {
        return this.get('model').get('currentUserPermissions').indexOf('admin') >= 0;
    }),
    // TODO: check vs comments PR logic etc
    canEdit: Ember.computed('isAdmin', 'isRegistration', function() {
        return this.get('isAdmin') && !(this.get('model').get('registration'));
    }),

    showModalAddContributors: false,
    actions: {
        toggleAddContributorModal() {
            this.toggleProperty('showModalAddContributors');
        },
        removeContributor(contrib) {
            this._super(...arguments);
            this.get('contributors').removeObject(contrib);
        },
        updateContributors(contributors, permissionsChanges, bibliographicChanges) {
            this._super(...arguments);
            // TODO how to send multiple save actions in a row without reload?
            window.location.reload();
        }

    }
});
