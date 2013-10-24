<%inherit file="base.mako"/>
<%def name="title()">Explore</%def>
<%def name="content()">
<%
    from framework import get_user
%>

  <div class="row">
    <div class="col-md-3 col-sm-4 sidebar">
        <ul class="nav nav-stacked nav-pills">
            <li><a href='#newPublicProjects'>Newest Public Projects</a></li>
            <li><a href='#newPublicRegistrations'>Newest Public Registrations</a></li>
            <li><a href='#popularPublicProjects'>Most Viewed Public Projects</a></li>
            <li><a href='#popularPublicRegistrations'>Most Viewed Public Registrations</a></li>
        </ul>
    </div><!-- end sidebar -->

    <div class="col-md-9 col-sm-8">
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
            <h3>Most Viewed Public Projects</h3>
            <ul class='project-list list-group'>
                ${node_list(most_viewed_projects, prefix='most_viewed')}
            </ul>
        </section>
        <section id='popularPublicRegistrations'>
            <h3>Most Viewed Public Registrations</h3>
            <ul class='project-list list-group'>
                ${node_list(most_viewed_registrations, prefix='most_viewed')}
            </ul>
        </section>
    </div>
  </div><!-- /.row -->


    <%def name="node_list(nodes, default=0, prefix='', metric='hits')">
    %for node in nodes:
        <%
            #import locale
            #locale.setlocale(locale.LC_ALL, 'en_US')
            unique_hits, hits = (
                 #locale.format('%d', val, grouping=True) if val else
                 #locale.format(0, val, grouping=True)
                val if val else 0
                for val in node.get_stats()
            )
            explicit_date = '{month} {dt.day} {dt.year}'.format(
                dt=node.date_created.date(),
                month=node.date_created.date().strftime('%B')
            )
        %>
        <li class="project list-group-item">
            <h4 class="list-group-item-heading">
                <a href="${node.url}">${node.title}</a>
            </h4>
                % if metric == 'hits':
                    <span class="badge" rel='tooltip' data-original-title='${hits} hits (${unique_hits} unique)'>
                        ${hits} views
                    </span>
                % elif metric == 'date_created':
                    <span class="badge" rel='tooltip' data-original-title='Created: ${explicit_date}'>
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
