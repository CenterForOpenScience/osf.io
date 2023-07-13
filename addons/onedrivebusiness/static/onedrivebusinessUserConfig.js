/**
* Module that controls the OneDrive for Office365 user settings. Includes Knockout view-model
* for syncing data.
*/

require('js/osfToggleHeight');

const osfHelpers = require('js/osfHelpers');


function ViewModel() {
    const self = this;
    self.properName = 'OneDrive for Office365';
}

function OneDriveBusinessUserConfig(selector) {
    // Initialization code
    const self = this;
    self.selector = selector;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel();
    osfHelpers.applyBindings(self.viewModel, self.selector);
}

module.exports = {
    OneDriveBusinessViewModel: ViewModel,
    OneDriveBusinessUserConfig: OneDriveBusinessUserConfig
};
