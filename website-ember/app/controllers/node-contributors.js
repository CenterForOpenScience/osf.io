import Ember from 'ember';

export default Ember.Controller.extend({
    contributors: Ember.A(),

    isContributor: Ember.computed('user', 'contributors', function() {
        // Is a contributor if userId in list of known contributors
        return !!this.get('contributors').findBy('userId', this.get('user.id'));
    }),

    canEdit: true, // TODO: Implement based on comments PR logic

    showModalAddContributors: false,
    actions: {
        toggleAddContributorModal() {
            this.toggleProperty('showModalAddContributors');
        }
    }
});
