// TODO Remove when @caneruguz's updates are in
require('css/projectorganizer.css');
///////////////////////////////////////////////

function makeIcon(className) {
    var icon = document.createElement('i');
    icon.className = className;
    return icon;
}

module.exports = {
    componentIcons: {
        hypothesis: makeIcon('fa fa-lightbulb-o'),
        methods_and_measures: makeIcon('fa fa-pencil'),
        procedure: makeIcon('fa fa-cogs'),
        instrumentation: makeIcon('fa fa-flask'),
        data: makeIcon('fa fa-database'),
        analysis: makeIcon('fa fa-bar-chart'),
        communication: makeIcon('fa fa-comment'),
        other: makeIcon('fa fa-question'),
        '': makeIcon('fa fa-circle-thin')
    },
    projectIcons: {
        folder: makeIcon('project-organizer-icon-folder'),
        smartFolder: makeIcon('project-organizer-icon-smart-folder'),
        project: makeIcon('project-organizer-icon-project'),
        registration: makeIcon( 'project-organizer-icon-reg-project'),
        component: makeIcon( 'project-organizer-icon-component'),
        registeredComponent: makeIcon( 'project-organizer-icon-reg-component'),
        link: makeIcon( 'project-organizer-icon-pointer')
    }
};
