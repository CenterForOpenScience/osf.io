import Ember from 'ember';

export default Ember.Controller.extend({
    fileDetail: Ember.inject.controller(),
    activeVersion: Ember.computed.alias('fileDetail.activeVersion'),
});
