<%inherit file="../base.mako"/>

<%def name="content()">

<%include file="project_header.mako"/>


${next.body()}


<%include file="../include/comment_template.mako" />
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

    // TODO: Put these in the contextVars object below
    var userId = '${user_id}';
    var nodeId = '${node['id']}';
    var userApiUrl = '${user_api_url}';
    var nodeApiUrl = '${node['api_url']}';
    // Mako variables accessible globally
    window.contextVars = {
        currentUser: {
            username: '${user.get("username")}'
        }
    }

    $(function() {

        $logScope = $('#logScope');
        // Get project data from the server and initiate KO modules
        $.getJSON(nodeApiUrl, function(data){
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
        );
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
        trackPiwik('${ piwik_host }', ${ node['piwik_site_id'] });
    });
</script>
% endif

<script>

    var $comments = $('#comments');
    var userName = '${user_full_name}';
    var canComment = ${'true' if node['can_comment'] else 'false'};
    var hasChildren = ${'true' if node['has_children'] else 'false'};

    if ($comments.length) {

        $script(['/static/js/commentpane.js', '/static/js/comment.js'], 'comments');

        $script.ready('comments', function () {
            var commentPane = new CommentPane('#commentPane');
            Comment.init('#comments', userName, canComment, hasChildren);
        });

    }

</script>

</%def>
