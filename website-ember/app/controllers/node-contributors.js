import Ember from 'ember';

export default Ember.Controller.extend({
    canEdit: true, // TODO: Implement based on comments PR logic

    showModalAddContributors: false,
    dummyVal: 'bob!',
    actions: {
        toggleAddContributorModal() {
            console.log('hit handler');
            this.toggleProperty('showModalAddContributors');
        }
    }
});
