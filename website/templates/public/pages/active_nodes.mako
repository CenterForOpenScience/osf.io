<%inherit file="base.mako"/>

<%def name="title()">Public Activity</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/public-activity-page.css">
</%def>

<%def name="content()">
    <%
        from framework.auth import get_user
    %>
    <div class="row">
        <div class="col-sm-4 col-md-3 affix-parent scrollspy">
            <div data-spy="affix" data-offset-bottom="250"  data-offset-top="60" class="panel panel-default m-t-lg hidden-print hidden-xs affix osf-affix" role="complementary">
                <ul class="nav nav-stacked nav-pills">
                    <li><a href='#newPublicProjects'>Newest public projects</a></li>
                    <li><a href='#newPublicRegistrations'>Newest public registrations</a></li>
                    <li><a href='#popularPublicProjects'>Popular public projects</a></li>
                    <li><a href='#popularPublicRegistrations'>Popular public registrations</a></li>
                </ul>
            </div>
        </div>
        <div class="col-sm-8 col-md-9" role="main" class="m-t-lg">
            <h1 class="page-header">Public Activity</h1>
            <section id='newPublicProjects'>
                <h3 class='anchor'>Newest public projects</h3>
                <div class='project-list'>
                    ${node_list(recent_apublic_projects, prefix='newest_public', metric='date_created')}
                </div>
            </section>
            <section id='newPublicRegistrations' class="m-t-lg">
                <h3 class='anchor'>Newest public registrations</h3>
                <div class='project-list'>
                    ${node_list(recent_public_registrations, prefix='newest_public', metric='registered_date')}
                </div>
            </section>
            <section id='popularPublicProjects' class="m-t-lg">
                <h3 class='anchor'>Popular public projects</h3>
                <div class='project-list'>
                    ${node_list(popular_public_projects, prefix='most_viewed', metric='hits')}
                </div>
            </section>
            <section id='popularPublicRegistrations' class="m-t-lg">
                <h3 class='anchor'>Popular public registrations</h3>
                <div class='project-list'>
                    ${node_list(popular_public_registrations, prefix='most_viewed', metric='hits')}
                </div>
            </section>
        </div>
    </div>

    <%def name="node_list(nodes, default=0, prefix='', metric='hits')">
        % for node in nodes:
            <%
                #import locale
                #locale.setlocale(locale.LC_ALL, 'en_US')
                if node.is_registration:
                    explicit_date = '{month} {dt.day} {dt.year}'.format(
                        dt=node.registered_date.date(),
                        month=node.registered_date.date().strftime('%B')
                    )
                else:
                    explicit_date = '{month} {dt.day} {dt.year}'.format(
                    dt=node.date_created.date(),
                    month=node.date_created.date().strftime('%B')
                )

            %>
            <div class="project osf-box p-sm m-b-sm">
                <div class="row">
                    <div class="col-md-10">
                        <h4 class="f-w-md overflow" style="width:85%">
                            <a href="${node.url}">${node.title}</a>
                        </h4>
                    </div>
                    <div class="col-md-2">
                        % if metric == 'hits':
                            <span class="project-meta pull-right" rel='tooltip' data-original-title='${ hits[node._id].get('hits') } views (${ hits[node._id].get('visits') } visits)'>
                                ${ hits[node._id].get('hits') }&nbsp;views (last&nbsp;week)
                            </span>
                        % elif metric == 'date_created':
                            <span class="project-meta pull-right" rel='tooltip' data-original-title='Created: ${explicit_date}'>
                                ${node.date_created.date()}
                            </span>
                        % elif metric == 'registered_date':
                            <span class="project-meta pull-right" rel='tooltip' data-original-title='Registered: ${explicit_date}'>
                                ${node.registered_date.date()}
                            </span>
                        % endif
                    </div>
                </div>
                <!-- Show abbreviated contributors list -->
                <div mod-meta='{
                    "tpl": "util/render_users_abbrev.mako",
                    "uri": "${node.api_url}contributors_abbrev/",
                    "kwargs": {
                        "node_url": "${node.url}"
                    },
                    "replace": true
                }'></div>
            </div>
        % endfor
    </%def>
</%def>
