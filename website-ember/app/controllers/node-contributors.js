import Ember from 'ember';

export default Ember.Controller.extend({
    canEdit: true, // TODO: Implement based on comments PR logic

    showModalAddContributors: false,
    actions: {
        toggleAddContributorModal() {
            this.toggleProperty('showModalAddContributors');
        }
    }
});
