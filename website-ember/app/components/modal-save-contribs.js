import Ember from 'ember';

export default Ember.Component.extend({
    isOpen: false,
    actions: {
        updateContributors() {
            this.sendAction('updateContributors');
            this.set('isOpen', false);
            this.sendAction('refreshView');
        },
        close() {
            this.set('isOpen', false);
        }
    }
});
