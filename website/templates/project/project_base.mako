<%inherit file="../base.mako"/>

<%def name="content()">

<%include file="project_header.mako"/>


${next.body()}


<%include file="modal_add_contributor.mako"/>
<%include file="modal_add_pointer.mako"/>
<%include file="modal_show_links.mako"/>
% if node['category'] == 'project':
    <%include file="modal_add_component.mako"/>
% endif
</%def>


<%def name="javascript_bottom()">
<% import json %>
<script>
    // Import modules
    $script(['/static/js/nodeControl.js'], 'nodeControl');
    $script(['/static/js/logFeed.js'], 'logFeed');
    $script(['/static/js/contribAdder.js'], 'contribAdder');

    // TODO: pollution! namespace me
    var userId = '${user_id}';
    var nodeId = '${node['id']}';
    var userApiUrl = '${user_api_url}';
    var nodeApiUrl = '${node['api_url']}';

    $(function() {

        $logScope = $('#logScope');
        // Get project data from the server and initiate KO modules
        $.ajax({
            type: 'get',
            url: nodeApiUrl,
            contentType: 'application/json',
            dataType: 'json',
            cache: false,
            success: function(data){
               // Initialize nodeControl and logFeed on success
               $script
                .ready('nodeControl', function() {
                    var nodeControl = new NodeControl('#projectScope', data);
                })
                .ready('logFeed', function() {
                    if ($logScope.length) { // Render log feed if necessary
                        var logFeed = new LogFeed('#logScope', data.node.logs, nodeApiUrl+'log/');
                    }
                });
                // If user is a contributor, initialize the contributor modal
                // controller
                if (data.user.can_edit) {
                    $script.ready('contribAdder', function() {
                        var contribAdder = new ContribAdder(
                            '#addContributorsScope',
                            data.node.title,
                            data.parent_node.id,
                            data.parent_node.title
                        );
                    });
                }
            }
        });
        // TODO: move AddPointerViewModel to its own module
        var $addPointer = $('#addPointer');
        var addPointerVM = new AddPointerViewModel(${json.dumps(node['title'])});
        ko.applyBindings(addPointerVM, $addPointer[0]);
        $addPointer.on('hidden.bs.modal', function() {
            addPointerVM.clear();
        });

        var linksModal = $('#showLinks')[0];
        var linksVM = new LinksViewModel(linksModal);
        ko.applyBindings(linksVM, linksModal);
    });

    // Make unregistered contributors claimable
    if (!userId) { // If no user logged in, allow user claiming
        $script(['/static/js/accountClaimer.js'], function() {
            var accountClaimer = new OSFAccountClaimer('.contributor-unregistered');
        });
    }

</script>
% if node.get('is_public') and node.get('piwik_site_id'):
<script type="text/javascript">
    $(function() {
        // Note: Don't use cookies for global site ID; cookies will accumulate
        // indefinitely and overflow uwsgi header buffer.
        trackPiwik('${ piwik_host }', ${ node['piwik_site_id'] });
    });
</script>
% endif
</%def>
