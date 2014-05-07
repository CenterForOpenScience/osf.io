<%inherit file="base.mako"/>
<%def name="title()">Explore</%def>
<%def name="content()">
<%
    from framework.auth import get_user
%>

  <div class="row">
    <div class="col-md-3">
        <div data-spy="affix" class="sidebar affix hidden-print" role="complementary">
            <ul class="nav nav-stacked nav-pills">
                <li><a href='#newPublicProjects'>Newest Public Projects</a></li>
                <li><a href='#newPublicRegistrations'>Newest Public Registrations</a></li>
                <li><a href='#popularPublicProjects'>Popular Public Projects</a></li>
                <li><a href='#popularPublicRegistrations'>Popular Public Registrations</a></li>
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-md-9" role="main">
      <h1 class="page-header">Public Activity</h1>
        <section id='newPublicProjects'>
            <h3>Newest Public Projects</h3>
            <ul class='project-list list-group'>
                ${node_list(recent_public_projects, prefix='newest_public', metric='date_created')}
            </ul>
        </section>
        <section id='newPublicRegistrations'>
            <h3>Newest Public Registrations</h3>
            <ul class='project-list list-group'>
                ${node_list(recent_public_registrations, prefix='newest_public', metric='date_created')}
            </ul>
        </section>
        <section id='popularPublicProjects'>
            <h3>Popular Public Projects</h3>
            <ul class='project-list list-group'>
                ${node_list(popular_public_projects, prefix='most_viewed', metric='hits')}
            </ul>
        </section>
        <section id='popularPublicRegistrations'>
            <h3>Popular Public Registrations</h3>
            <ul class='project-list list-group'>
                ${node_list(popular_public_registrations, prefix='most_viewed', metric='hits')}
            </ul>
        </section>
    </div>
  </div><!-- /.row -->


    <%def name="node_list(nodes, default=0, prefix='', metric='hits')">
    %for node in nodes:
        <%
            #import locale
            #locale.setlocale(locale.LC_ALL, 'en_US')
            explicit_date = '{month} {dt.day} {dt.year}'.format(
                dt=node.date_created.date(),
                month=node.date_created.date().strftime('%B')
            )
        %>
        <li class="project list-group-item list-group-item-node">
            <h4 class="list-group-item-heading overflow" style="width:85%">
                <a href="${node.url}">${node.title}</a>
            </h4>
                % if metric == 'hits':
                    <span class="project-meta pull-right text-primary" rel='tooltip' data-original-title='${ hits[node._id].get('hits') } views (${ hits[node._id].get('visits') } visits)'>
                        ${ hits[node._id].get('hits') } views (in the past week)
                    </span>
                % elif metric == 'date_created':
                    <span class="project-meta pull-right text-primary" rel='tooltip' data-original-title='Created: ${explicit_date}'>
                        ${node.date_created.date()}
                    </span>
                % endif

            <!-- Show abbreviated contributors list -->
            <div mod-meta='{
                    "tpl": "util/render_users_abbrev.mako",
                    "uri": "${node.api_url}contributors_abbrev/",
                    "kwargs": {
                        "node_url": "${node.url}"
                    },
                    "replace": true
                }'>
            </div>

        </li>
    %endfor
    </%def>
</%def>
