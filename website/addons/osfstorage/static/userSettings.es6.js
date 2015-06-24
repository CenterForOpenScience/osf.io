var m = require('mithril');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');


var PROGRESSBARSTYLE = '.progress-bar.progress-bar-info';
var PROGRESSERRORBARSTYLE = '.progress-bar.progress-bar-danger';
var PROGRESSLOADINGBARSTYLE = '.progress-bar.progress-bar-info.progress-bar-striped.active';


function OsfStorageUserSettingsController() {
    var self = this;

    self.usage = 100; // Fill the progress bar initially
    self.rawUsage = 100;
    self.usageLimit = 100;
    self.percentUsage = 100;
    self.text = 'Loading...';
    self.progressStyle = PROGRESSLOADINGBARSTYLE;

    m.request({
        method: 'GET',
        background: true,
        url: '/api/v1/osfstorage/usage/',
    }).then(function(resp) {
        self.rawUsage = resp.user.storageUsage;
        self.rawUsageLimit = resp.user.storageLimit;
        self.usage = $osf.humanFileSize(resp.user.storageUsage, true);
        self.usageLimit = $osf.humanFileSize(resp.user.storageLimit, true);
        self.percentUsage = Math.ceil(self.rawUsage / self.rawUsageLimit * 100);
        self.collabUsage = $osf.humanFileSize(resp.contributed.storageUsage, true);

        self.progressStyle = PROGRESSBARSTYLE;
        self.text = `${self.usage} used (${self.percentUsage}%)`;
    }, function() {
        self.text = 'Unable to load';
        self.progressStyle = PROGRESSERRORBARSTYLE;
    }).then(m.redraw, m.redraw);

    self.helpModal = function() {
        bootbox.alert({
            title: 'OSF Storage file limits',
            message: `
            OSF is a repository for storing files.<br>
            It is not feasible for OSF to store all files at scale.<br>
            As such, users must be limited to standardized quotas for the amount of file storage that OSF can provide for free.<br>
            Users should also have access to information about their storage use and limits.`
        });
    };
}


function OsfStorageUserSettingsView(ctrl) {
    return m('div', [
        m('h4.addon-title', [
            'OSF Storage ',
            m('i.fa.fa-question-circle.pointer.pull-right', {onclick: ctrl.helpModal})
        ]),
        m('p', !ctrl.collabUsage ? '' :
            `In total, all projects you are a collaborator on have ${ctrl.collabUsage} of data`
        ),
        m('.progress', [
            m(ctrl.progressStyle, {
                role: 'progressbar',
                'aria-valuemin': 0,
                'aria-valuenow': ctrl.rawUsage,
                'aria-valuemax': ctrl.rawUsageLimit,
                style: {width: `${ctrl.percentUsage}%`},
            }, m('', {style:{right:0,left:0,position:'absolute',color:'#333'}}, ctrl.text))
        ])
    ]);
}



module.exports = {
    view: OsfStorageUserSettingsView,
    controller: OsfStorageUserSettingsController
};
