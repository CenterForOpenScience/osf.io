<%inherit file="contentContainer.mako"/>

## todo: move to warnings.py
<%
    make_public_warning = 'Once a project is made public, there is no way to guarantee that access to the data it contains can be complete prevented. Users should assume that once a project is made public, it will always be public. Are you absolutely sure you would like to continue?'
    make_private_warning = 'Making a project will prevent users from viewing it on this site, but will have no impact on external sites, including Google\'s cache. Would you like to continue?'
%>

% if node_is_registration:
    <span class="label label-important" style="font-size:1.1em;margin-bottom:30px;">This node is a registration of <a href="${node_registered_from_url}">this node</a>; the content of the node has been frozen and cannot be edited.</span>
    <style type="text/css">
    .watermarked {
        background-image:url('/static/read-only.png');
        background-repeat:repeat;
    }
    </style>
%endif

<header class="jumbotron subhead" id="overview">

    <div class="row">

        <div class="btn-toolbar pull-right">
            <div class="btn-group">
            %if not node_is_public:
                <button class='btn btn-default disabled'>Private</button>
                % if user_is_contributor:
                    <a class="btn btn-warning" href="${node_url}permissions/public/" data-confirm="${make_public_warning}">Make public</a>
                % endif
            %else:
                % if user_is_contributor:
                    <a class="btn btn-default" href="${node_url}permissions/private/" data-confirm="${make_private_warning}">Make private</a>
                % endif
                <button class="btn btn-warning disabled">Public</button>
            %endif
            </div>

            <div class="btn-group">
                % if user_name:
                    <button rel="tooltip" title="Watch" class="btn btn-default" href="#" onclick="NodeActions.toggleWatch()">
                % else:
                    <button rel="tooltip" title="Watch" class="btn btn-default disabled" href="#">
                % endif
                <i class="icon-eye-open"></i>
                % if not user_is_watching:
                    <span id="watchCount">Watch&nbsp;${node_watched_count}</span>
                % else:
                    <span id="watchCount">Unwatch&nbsp;${node_watched_count}</span>
                % endif
                  </button>

                <button
                    rel="tooltip"
                    title="Number of times this node has been forked (copied)"
                    % if node_category == 'project' and user_name:
                        href="#"
                        class="btn btn-default"
                        onclick="NodeActions.forkNode();"
                    % else:
                        class="btn disabled"
                    % endif
                >
                    <i class="icon-code-fork"></i>&nbsp;${node_fork_count}
                </button>
            </div>
        </div>

        %if user_can_edit:
            <script>
                $(function() {
                    function urlDecode(str) {
                        return decodeURIComponent((str+'').replace(/\+/g, '%20'));
                    }

                    $('#node-title-editable').editable({
                       type:  'text',
                       pk:    '${node_id}',
                       name:  'title',
                       url:   '${node_api_url}edit/',
                       title: 'Edit Title',
                       placement: 'bottom',
                       value: "${ '\\\''.join(node_title.split('\'')) }",
                       success: function(data){
                            document.location.reload(true);
                       }
                    });
                });
            </script>
        %endif

        <div class="span4">

            %if parent_id:
                <h1 id="node-title" style="display:inline-block" class="node-parent-title"><a href="/project/${parent_id}/">${parent_title}</a> / </h1>
            %endif
            <h1 id="${'node-title-editable' if user_can_edit else 'node-title'}" class='node-title' style="display:inline-block">${node_title}</h1>

            <p id="contributors">Contributors:
                <div mod-meta='{"tpl" : "project/render_contributors.html", "uri" : "${node_api_url}get_contributors/", "replace" : true}'></div>
            % if node_is_fork:
                <br />Forked from <a href="${node_forked_from_url}">${node_forked_from_url}</a> on ${node_forked_date}
            %endif
            % if node_is_registration and node_registered_meta:
                <br />Registration Supplement:
                % for meta in node_registered_meta:
                    <a href="${node_url}register/${meta['name_no_ext']}">${meta['name_clean']}</a>
                % endfor
            %endif
            <br />Date Created:
                <span class="date">${node_date_created}</span>
            | Last Updated:
            %if not node:
                <span class="date">${node_date_modified}</span>
            %else:
                <span class="date">${node_date_modified}</span>
            %endif

            %if node:
                <br />Category: ${node_category}
            %else:
                %if node_description:
                <br />Description: ${node_description}
                %endif
            %endif
            </p>

        </div>

    </div>

    <div class="subnav">
        <ul class="nav nav-pills">
            <li><a href="${node_url}">Dashboard</a></li>
            <li><a href="${node_url}wiki/">Wiki</a></li>
            <li><a href="${node_url}statistics/">Statistics</a></li>
            <li><a href="${node_url}files/">Files</a></li>
            <li><a href="${node_url}registrations/">Registrations</a></li>
            <li><a href="${node_url}forks/">Forks</a></li>
            % if user_is_contributor:
            <li><a href="${node_url}settings/">Settings</a></li>
            %endif
        </ul>
    </div>
</header>
<!-- TODO: Move this out of html -->
<script type="text/javascript">
  var App = Ember.Application.create();

  App.RadioButton = Ember.View.extend({
    classNames: ['ember-radiobox'],
    tagName: "input",
    attributeBindings: ['type', 'name', 'value'],

    type: "radio",

    name: "id",

    value: "",
  });

  App.Gravatar = Ember.View.extend({
    classNames: ['ember-gravatar'],
    tagName: "img",
    attributeBindings: ['src'],
  });

  App.SearchController = Ember.Object.create({
    has_started: false,
    is_email: null,
    content: [],
    search_type:'users',
    add:function(){
        var emthis = this;
        var user = this.user;
        var fullname = this.fullname;
        var email = this.email;

        if ( fullname ){
                jQuery.post(
                    '${node_api_url}addcontributor/',
                    { fullname: fullname, email: email },
                    function(data){
                        $('#addContributors').modal('hide');
                        window.location.reload();
                    },
                    'json'
                );
        }else{
            if ( $('input[name=id]:checked').length > 0 ){
                jQuery.post(
                    '${node_api_url}addcontributor/',
                    { user_id:$('input[name=id]:checked')[0].value },
                    function(data){
                        $('#addContributors').modal('hide');
                        window.location.reload();
                    },
                    'json'
                );
            }
        }
    },
    search: function() {
        var emthis = this;
        var query = this.query;
        jQuery.post(
            '/api/v1/search/users/',
            {query:query},
            function(data){
                emthis.set('has_started', true);
                emthis.set('is_email', data['is_email']);
                emthis.set('content', []);
                emthis.set('content', data['results']);
            },
            'json'
        );
    },
  });
</script>
<div class="modal fade" id="addContributors">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Add Contributors</h3>
            </div><!-- end modal-header -->
            <div class="modal-body">
                <script type="text/x-handlebars">
                {{view Ember.TextField valueBinding="App.SearchController.query"}}
                {{#view Em.Button target="App.SearchController" action="search"}}
                    Search
                {{/view}}
                <br />
                {{#if App.SearchController.content}}
                    {{#each App.SearchController.content}}
                        {{#view App.RadioButton value=id fullname=fullname}}
                            {{fullname}}
                        {{/view}}
                        {{#view App.Gravatar src=gravatar}}
                        {{/view}}
                        <br />
                        ##<input type="radio" name="id" value="{{id}}">&nbsp;{{fullname}}<br />
                    {{/each}}
                {{else}}
                    {{#if App.SearchController.has_started}}
                        {{#if App.SearchController.is_email}}
                            No user by that email address found.
                        {{else}}
                            No user by that name found.
                        {{/if}}
                         You can manually add the person you are looking for by entering their name and email address below.  They can later claim this project via that email address when they associate said address with an OSF account. <br />
                            <br />
                            <form class="form-horizontal">
                            <div class="form-group">
                            <label>Full name</label><div>{{view Ember.TextField valueBinding="App.SearchController.fullname"}}</div>
                            <label>Email</label><div>{{view Ember.TextField valueBinding="App.SearchController.email"}}</div>
                            </div>
                            </form>
                    {{/if}}
                {{/if}}
                </script>
            </div><!-- end modal-body -->
            <div class="modal-footer">
                <a href="#" class="btn" data-dismiss="modal">Cancel</a>
                <button onclick="App.SearchController.add()" class="btn primary">Add</button>
            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

${next.body()}
