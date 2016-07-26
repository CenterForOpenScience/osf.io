import Ember from 'ember';

export default Ember.Component.extend({
    removeSelf: Ember.computed('contributorToRemove', 'currentUser', function() {
        if (this.get('contributorToRemove')) {
            return this.get('contributorToRemove').id.split('-')[1] === this.get('currentUser').id;
        } else {
            return false;
        }
    }),
    actions: {
        removeContributor(contrib) {
            this.sendAction('removeContributor', contrib);
        },
    }
});
