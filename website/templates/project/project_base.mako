<%inherit file="../base.mako"/>

<%def name="content()">

<%include file="project_header.mako"/>


${next.body()}



<%include file="modal_generate_private_link.mako"/>
<%include file="modal_add_contributor.mako"/>
<%include file="modal_add_pointer.mako"/>
<%include file="modal_show_links.mako"/>
% if node['category'] == 'project':
    <%include file="modal_add_component.mako"/>
    <%include file="modal_duplicate.mako"/>
% endif
</%def>


<%def name="javascript_bottom()">
<script>
    // Import modules
    $script(['/static/js/nodeControl.js'], 'nodeControl');
    $script(['/static/js/logFeed.js'], 'logFeed');
    $script(['/static/js/contribAdder.js'], 'contribAdder');
    $script(['/static/js/pointers.js'], 'pointers');
    %if 'badges' in addons_enabled and badges and badges['can_award']:
    $script(['/static/addons/badges/badge-awarder.js'], function() {
        attachDropDown('${'{}badges/json/'.format(user_api_url)}');
    });

    %endif
    // TODO: Put these in the contextVars object below
    var nodeId = '${node['id']}';
    var userApiUrl = '${user_api_url}';
    var nodeApiUrl = '${node['api_url']}';
    // Mako variables accessible globally
    window.contextVars = {
        currentUser: {
            username: '${user.get("username")}',
            id: '${user_id}'
        },
        node: {
            title: "${node['title']}"
        }
    };

    $(function() {

        $logScope = $('#logScope');
        $linkScope= $("#linkScope");
        // Get project data from the server and initiate KO modules
        $.getJSON(nodeApiUrl, function(data){
               // Initialize nodeControl and logFeed on success
               $script
                .ready('nodeControl', function() {
                    var nodeControl = new NodeControl('#projectScope', data);
                })
                .ready('logFeed', function() {
                    if ($logScope.length) { // Render log feed if necessary
                        var logFeed = new LogFeed('#logScope', data.node.logs, {'url':nodeApiUrl+'log/', 'hasMoreLogs': data.node.has_more_logs});
                    }
                });
                // If user is a contributor, initialize the contributor modal
                // controller
                if (data.user.can_edit) {
                    $script.ready('contribAdder', function() {
                        var contribAdder = new ContribAdder(
                            '#addContributors',
                            data.node.title,
                            data.parent_node.id,
                            data.parent_node.title
                        );
                    });
                }

            }
        );



        var linksModal = $('#showLinks')[0];
        var linksVM = new LinksViewModel(linksModal);
        ko.applyBindings(linksVM, linksModal);
    });

    $script.ready('pointers', function() {
        var pointerManager = new PointerManager('#addPointer', contextVars.node.title);
    });

    // Make unregistered contributors claimable
    % if not user.get('is_contributor'):
    $script(['/static/js/accountClaimer.js'], function() {
        var accountClaimer = new OSFAccountClaimer('.contributor-unregistered');
    });
    % endif

</script>
% if node.get('is_public') and node.get('piwik_site_id'):
<script type="text/javascript">
    $(function() {
        // Note: Don't use cookies for global site ID; cookies will accumulate
        // indefinitely and overflow uwsgi header buffer.
        $.osf.trackPiwik('${ piwik_host }', ${ node['piwik_site_id'] });
    });
</script>
% endif

</%def>
