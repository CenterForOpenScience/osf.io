<%inherit file="base.mako"/>
<%def name="title()">RSS</%def>
<%def name="content()">
<%
    from framework.auth import get_user
%>

  <div class="row">

    <div class="col-md-9" role="main">
      <h1 class="page-header">RSS Feed</h1>
        <section id='newPublicProjects'>
            <h3>Newest Public Projects</h3>
            <ul class='project-list list-group'>
                ${node_list(recent_public_projects, prefix='newest_public', metric='date_created')}
            </ul>
        </section>
        
    </div>
  </div><!-- /.row -->


  <%def name="node_list(nodes, default=0, prefix='', metric='hits')">
    %for node in nodes:
        <%
            explicit_date = '{month} {dt.day} {dt.year}'.format(
                dt=node.date_created.date(),
                month=node.date_created.date().strftime('%B')
            )
            print node
        %>
        <li>
            <h4>${node.title}</h4>
            <h4>${node._id}</h4>
            </h4>${node.date_created.date()}</h4>
        </li>
<!--         <li class="project list-group-item list-group-item-node">
            <div class="row">
                <div class="col-md-10">
                    <h4 class="list-group-item-heading overflow" style="width:85%">
                        <a href="${node.url}">${node.title}</a>
                    </h4>
                </div>
                <div class="col-md-2">
                    % if metric == 'hits':
                        <span class="project-meta pull-right text-primary" rel='tooltip' data-original-title='${ hits[node._id].get('hits') } views (${ hits[node._id].get('visits') } visits)'>
                            ${ hits[node._id].get('hits') } views (in the past week)
                        </span>
                    % elif metric == 'date_created':
                        <span class="project-meta pull-right text-primary" rel='tooltip' data-original-title='Created: ${explicit_date}'>
                            ${node.date_created.date()}
                        </span>
                    % endif
                </div>
            </div> -->
            <!-- Show abbreviated contributors list
            <div mod-meta='{
                    "tpl": "util/render_users_abbrev.mako",
                    "uri": "${node.api_url}contributors_abbrev/",
                    "kwargs": {
                        "node_url": "${node.url}"
                    },
                    "replace": true
                }'>
            </div>

        </li> -->
    %endfor
  </%def>
</%def>
