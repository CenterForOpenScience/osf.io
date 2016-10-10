import Ember from 'ember';

export default Ember.Controller.extend({
    fileDetail: Ember.inject.controller(),
    version: Ember.computed.alias('fileDetail.version'),
    sortedVersions: Ember.computed.alias('fileDetail.sortedVersions'),
    activeVersion: Ember.computed.alias('fileDetail.activeVersion'),
});
