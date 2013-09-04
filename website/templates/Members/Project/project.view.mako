<%inherit file="contentContainer.mako"/>

<%
    import framework
    import hashlib
    from website.project.model import Node
    url = framework.request.url
    contributors_text = []
    contributors_ids = []

    if node:
        node_to_use = node
        is_node = True
        is_project = False
    else:
        node_to_use = project
        is_node = False
        is_project = True

    user_is_contributor = node_to_use.is_contributor(user)
    editable = user_is_contributor and not node_to_use.is_registration

    # If a parent project exists, put it here so the title can be displayed.
    parent_project = None
    if node_to_use._b_node_parent:
        parent_project = Node.load(node_to_use._b_node_parent)


    for contributor in node_to_use.contributor_list:
        if "id" in contributor:
            contributor = framework.get_user(contributor["id"])
            txt = '<a href="/profile/%s"' % contributor.id
            if user_is_contributor:
                txt += ' class="user-quickedit" data-userid="%s" data-fullname="%s"' % (contributor.id, contributor.fullname)
            txt += '>%s</a>' % contributor.fullname
            contributors_ids.append(contributor.id)
        else:
            if "nr_name" in contributor:
                txt = '<span class="user-quickedit" data-userid="nr-' + hashlib.md5(contributor["nr_email"]).hexdigest() + '" data-fullname="' + contributor["nr_name"] + '">' + contributor["nr_name"] + '</span>'

        contributors_text.append(txt)

    contributors_text = ', '.join(contributors_text)
    counterUnique, counterTotal = framework.get_basic_counters(
        '/project/%s/' % project.id)

    remove_url = "/project/" + project.id + "/"
    if node:
        remove_url += "node/" + node.id + "/"
    remove_url += "removecontributors"

    make_public_warning = 'Once a project is made public, there is no way to guarantee that access to the data it contains can be complete prevented. Users should assume that once a project is made public, it will always be public. Are you absolutely sure you would like to continue?'
    make_private_warning = 'Making a project will prevent users from viewing it on this site, but will have no impact on external sites, including Google\'s cache. Would you like to continue?'
%>

<script>

</script>



% if node_to_use.is_registration:
<span class="label label-important" style="font-size:1.1em;margin-bottom:30px;">This node is a registration of <a href="${node_to_use.registered_from.url()}">this node</a>; the content of the node has been frozen and cannot be edited.</span>
    <style type="text/css">
.watermarked {
  background-image:url('/static/read-only.png');
  background-repeat:repeat;
}
</style>
%endif

<header class="jumbotron subhead" id="overview">
    <div class="btn-toolbar" style="float:right;">
        <div class="btn-group">
        %if not node_to_use.is_public:
            <button class='btn disabled'>Private</button>
            % if editable:
                %if node:
                    <a class="btn" href="/project/${project.id}/node/${node.id}/makepublic" data-confirm="${make_public_warning}">Make public</a>
                %else:
                    <a class="btn" href="/project/${project.id}/makepublic" data-confirm="${make_public_warning}">Make public</a>
                %endif
            % endif
        %else:
            % if editable:
                %if node:
                    <a class="btn" href="/project/${project.id}/node/${node.id}/makeprivate" data-confirm="${make_private_warning}">Make private</a>
                %else:
                    <a class="btn" href="/project/${project.id}/makeprivate" data-confirm="${make_private_warning}">Make private</a>
                %endif
            % endif
            <button class="btn disabled">Public</button>
        %endif
        </div>

        <div class="btn-group">
          <a rel="tooltip" title="Coming soon: Number of users watching this node" class="btn disabled" href="#"><i class="icon-eye-open"></i>&nbsp;${len(node_to_use.watchingUsers) if node_to_use.watchingUsers else 0}</a>
          <a
              rel="tooltip"
              title="Number of times this node has been forked (copied)"
              % if is_project and user is not None:
              href="#"
              class="btn"
              onclick="forkNode();"
              % else:
              class="btn disabled"
              % endif
          >
              <i class="icon-fork"></i>&nbsp;${len(node_to_use.node_forked) if node_to_use.node_forked else 0}
          </a>
        </div>
    </div>
    %if user_is_contributor and not node_to_use.is_registration:
    <script>
        $(function() {
            $('#node-title-editable').editable({
               type:  'text',
               pk:    '${node_to_use.id}',
               name:  'title',
               url:   '${node_to_use.url()}/edit',  
               title: 'Edit Title',
               placement: 'bottom',
               value: '${ '\\\''.join(node_to_use.title.split('\'')) }',
               success: function(data){
                    document.location.reload(true);
               }
            });
        });
    </script>

    %endif
    %if parent_project:
        <h1 id="node-title" style="display:inline-block"><a href="/project/${parent_project.id}/">${parent_project.title}</a> / </h1> <h1 id="${'node-title-editable' if node_to_use.is_contributor else 'node-title'}" style="display:inline-block">${node_to_use.title}</h1>
    %else:
        <h1 id="${'node-title-editable' if node_to_use.is_contributor else 'node-title'}" style="display:inline-block">${project.title}</h1>
    %endif
    <p id="contributors">Contributors: ${contributors_text} 
    % if user_is_contributor:
        | <a href="#addContributors" data-toggle="modal">add</a>
    %endif
    % if node_to_use.is_fork:
        <br />Forked from <a href="${node_to_use.forked_from.url()}">${node_to_use.forked_from.url()}</a> on ${node_to_use.forked_date.strftime('%Y/%m/%d %I:%M %p')}
    %endif
    % if node_to_use.is_registration and node_to_use.registered_meta:
        <br />Registration Supplement: ${', '. join([u'<a href="{url}/register/{k}">{kf}</a>'.format(url=node_to_use.url(), k=k.replace('.txt', ''), kf=str(k.replace('.txt', '').replace('_', ' '))) for k in node_to_use.registered_meta])}
    %endif
    <br />Date Created: 
    %if not node:
        <span class="date">${project.date_created.strftime('%Y/%m/%d %I:%M %p')}</span>
    %else:
        <span class="date">${node.date_created.strftime('%Y/%m/%d %I:%M %p')}</span>
    %endif
    | Last Updated: 
    %if not node:
        <span class="date">${project.logs.object(len(project.logs)-1).date.strftime('%Y/%m/%d %I:%M %p')}</span>
    %else:
        <span class="date">${node.logs.object(len(node.logs)-1).date.strftime('%Y/%m/%d %I:%M %p')}</span>
    %endif
    
    %if node:
        <br />Category: ${node.category}
    %else:
        %if project.description:
        <br />Description: ${project.description}
        %endif
    %endif
    </p>
    <div class="subnav">
        <ul class="nav nav-pills">
            <li><a href="${node_to_use.url()}">Dashboard</a></li>
            <li><a href="${node_to_use.url()}/wiki/">Wiki</a></li>
            <li><a href="${node_to_use.url()}/statistics">Statistics</a></li>
            <li><a href="${node_to_use.url()}/files">Files</a></li>
            <li><a href="${node_to_use.url()}/registrations">Registrations</a></li>
            <li><a href="${node_to_use.url()}/forks">Forks</a></li>
            % if user_is_contributor:
            <li><a href="${node_to_use.url()}/settings">Settings</a></li>
            %endif
        </ul>
    </div>
</header>
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
                    '${node_to_use.url()}/addcontributor',
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
                    '${node_to_use.url()}/addcontributor',
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
            '/search/users/',
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
<div class="modal hide fade" id="addContributors">
    <div class="modal-header">
        <h3>Add Contributors</h3>
    </div>
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
                    <label>Full name</label><div>{{view Ember.TextField valueBinding="App.SearchController.fullname"}}</div>
                    <label>Email</label><div>{{view Ember.TextField valueBinding="App.SearchController.email"}}</div>
                    </form>
            {{/if}}
        {{/if}}
        </script>
    </div>
    <div class="modal-footer">
        <a href="#" class="btn" data-dismiss="modal">Cancel</a> 
        <button onclick="App.SearchController.add()" class="btn primary">Add</button>
    </div>
</div>
${next.body()}