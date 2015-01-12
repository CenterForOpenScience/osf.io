var path = require('path');
var fs = require('fs');

var addons = require('./addons.json');
var root = path.join(__dirname, 'website', 'static');
/** Return the absolute path given a path relative to ./website/static */
var staticPath = function(dir) {
    return path.join(root, dir);
};

var entry = {
    'base-page': staticPath('js/pages/base-page.js'),
    'home-page': staticPath('js/pages/home-page.js'),
    'dashboard-page': staticPath('js/pages/dashboard-page.js'),
    'profile-page': staticPath('js/pages/profile-page.js'),
    'project-dashboard': staticPath('js/pages/project-dashboard-page.js'),
    'project-base-page': staticPath('js/pages/project-base-page.js'),
    'wiki-edit-page': staticPath('js/pages/wiki-edit-page.js'),
    'files-page': staticPath('js/pages/files-page.js'),
    'profile-settings-page': staticPath('js/pages/profile-settings-page.js'),
    'register_1-page': staticPath('js/pages/register_1-page.js'),
    'sharing-page': staticPath('js/pages/sharing-page.js'),
    'conference-page': staticPath('js/pages/conference-page.js'),
    'view-file-page': staticPath('js/pages/view-file-page.js'),
    'new-folder-page': staticPath('js/pages/new-folder-page.js'),
    'project-settings-page': staticPath('js/pages/project-settings-page.js'),
    'search-page': staticPath('js/pages/search-page.js'),
    'user-addon-cfg-page': staticPath('js/pages/user-addon-cfg-page.js'),
    'addon-permissions': staticPath('js/addon-permissions.js'),
    // Commons chunk
    'vendor': [
        'knockout',
        'knockout-validation',
        'bootstrap',
        'bootbox',
        'select2',
        'hgrid',
        'osfHelpers',
        'knockout-punches',
        'dropzone',
        'knockout-sortable',
        'dropzonePatch',
        'rubeus',
        'jquery.cookie'
    ]
};

// Collect adddons endpoints. If an addon's static folder has
// any of the following files, it will be added as an entry point
// and output to website/static/public/js/<addon-name>/files.js
var addonModules = ['files.js', 'node-cfg.js', 'user-cfg.js', 'file-detail.js', 'widget-cfg.js'];
addons.addons.forEach(function(addonName) {
    var baseDir = addonName + '/';
    addonModules.forEach(function(module) {
        var modulePath = path.join(__dirname, 'website', 'addons',
                                  addonName, 'static', module);
        if (fs.existsSync(modulePath)) {
            var entryPoint = baseDir + module.split('.')[0];
            entry[entryPoint] =  modulePath;
        }
    });
});

module.exports = entry;
