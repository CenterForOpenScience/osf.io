var DmptoolWidget = require('./dmptoolWidget.js');

var url = window.contextVars.node.urls.api + 'dmptool/widget/contents/';
// #dmptoolScope will only be in the DOM if the addon is properly configured
if ($('#dmptoolScope')[0]) {
    new DmptoolWidget('#dmptoolScope', url);
}
