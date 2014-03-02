<%inherit file="../base.mako"/>

<%def name="content()">

<%include file="project_header.mako"/>


${next.body()}


<%include file="modal_add_contributor.mako"/>
<%include file="modal_add_pointer.mako"/>
<%include file="modal_show_links.mako"/>
<%include file="modal_add_component.mako"/>
</%def>


<%def name="javascript_bottom()">
<% import json %>
<script>
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
                // Initialize ProjectViewModel with returned data
                $script(['/static/js/nodeControl.js'], function() {
                    var nodeControl = new NodeControl('#projectScope', data)
                });

                if (data.user.can_edit) {
                    // Initiate AddContributorViewModel
                    var $addContributors = $('#addContributorsScope');
                    var addContribVM = new AddContributorViewModel(
                        data.node.title,
                        data.parent_node.id,
                        data.parent_node.title
                    );
                    ko.applyBindings(addContribVM, $addContributors[0]);
                    // Clear user search modal when dismissed; catches dismiss by escape key
                    // or cancel button.
                    $addContributors.on('hidden.bs.modal', function() {
                        addContribVM.clear();
                    });
                }

                if ($logScope.length) { // Render log feed if necessary
                    $script(['/static/js/logFeed.js'], function() {
                        var logFeed = new LogFeed('#logScope', data.node.logs);
                    });
                }
            }
        });

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
