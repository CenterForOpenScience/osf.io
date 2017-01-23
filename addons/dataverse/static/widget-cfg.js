var DataverseWidget = require('./dataverseWidget.js');

var url = window.contextVars.node.urls.api + 'dataverse/widget/contents/';
// #dataverseScope will only be in the DOM if the addon is properly configured
if ($('#dataverseScope')[0]) {
    new DataverseWidget('#dataverseScope', url);
}
