import Ember from 'ember';

export default Ember.Component.extend({
    value: '',
    initializeAce: function(editor) {
        // TODO Ember and ace editor conflict here Issue https://github.com/emberjs/ember.js/issues/12903
        // editor.getSession().setMode('ace/mode/markdown');
        editor.getSession().setUseSoftTabs(true);   // Replace tabs with spaces
        editor.getSession().setUseWrapMode(true);   // Wraps text
        editor.renderer.setShowGutter(false);       // Hides line number
        editor.setShowPrintMargin(false);           // Hides print margin
        editor.commands.removeCommand('showSettingsMenu');  // Disable settings menu
        editor.setReadOnly(false); // Read only until initialized
        editor.setOptions({
            enableBasicAutocompletion: false,
            enableSnippets: false,
            enableLiveAutocompletion: false
        });
    },
    fileManager: Ember.inject.service(),
    actions: {
        saveFile(file) {
            var data = this.value;
            this.get('fileManager').updateContents(file, data);
        },
        revertFile(file) {
            var _this = this;
            _this.get('fileManager').getContents(file).then(function(contents) {
                _this.set('value', contents);
            });
        }
    },
});
