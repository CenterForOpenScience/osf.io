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
        addContributor(userId) {
            // Perform additional cleanup specific to this view to keep manually fetched contributors list in sync
            return this._super(...arguments).then((res) => {
                let contributors = this.get('contributors');
                let record = this.store.peekRecord('contributor', `${this.get('model.id')}-${userId}`);
                if (record) {
                    contributors.addObject(record);
                }
                // TODO: Is error handling needed (if record not found)?
                return res;
            });
        },
        removeContributor(contrib) {
            this._super(...arguments);
            this.get('contributors').removeObject(contrib);
        }
    }
});
