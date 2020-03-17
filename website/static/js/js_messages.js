var rdmGettext = require('js/rdmGettext');
var gt = rdmGettext.rdmGettext();
var _ = function(msgid) { return gt.gettext(msgid); };

var editBtn = _('Edit');

var newProjectCategory = [_('Analysis'),_('Communication'),_('Data'),_('Hypothesis'),_('Instrumentation'),_('Methods and Measures'),_('Procedure'),_('Project'),_('Software'),_('Other')];

var NODE_SUBSCRIPTIONS_AVAILABLE = [_('Comments added'),_('Files updated')];

var USER_SUBSCRIPTIONS_AVAILABLE = [_('Replies to your comments'),_('Comments added'),_('Files updated'),_('Mentions added'),_('Preprint submissions updated')];

var noLicense = _('No license');

var beforeFork = _('Because you have not configured the {addon} add-on, your authentication will not be transferred to the forked {category}. You may authorize and configure the {addon} add-on in the new fork on the settings page.');
