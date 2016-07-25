import Ember from 'ember';

/**
 * Modal that handles adding and removing contributors from a project
 * @class modal-add-contribs
 */
export default Ember.Component.extend({
    /**
     * @property {String} page Which page of the modal to display
     * @default whom|which|invite
     */
    page: 'whom'  // TODO: Replace this with components; temp feature
});
