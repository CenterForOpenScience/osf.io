<%inherit file="contentContainer.mako" />

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
    </div>

    <div class="col-md-9 col-sm-8">
      <h1 class="page-header">Public Activity</h1>
        <section id='newPublicProjects'>
            <h2>Newest Public Projects</h2>
            <ul class='project-list list-group'>
                ${node_list(recent_public_projects, prefix='newest_public', metric='date_created')}
            </ul>
        </section>
        <section id='newPublicRegistrations'>
            <h2>Newest Public Registrations</h2>
            <ul class='project-list list-group'>
                ${node_list(recent_public_registrations, prefix='newest_public', metric='date_created')}
            </ul>
        </section>
        <section id='popularPublicProjects'>
            <h2>Most Viewed Public Projects</h2>
            <ul class='project-list list-group'>
                ${node_list(most_viewed_projects, prefix='most_viewed')}
            </ul>
        </section>
        <section id='popularPublicRegistrations'>
            <h2>Most Viewed Public Registrations</h2>
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
        <h3 class="list-group-item-heading">
            <a href="${node.url}">${node.title}</a>
        </h3>
            % if metric == 'hits':
                <span class="badge" rel='tooltip' data-original-title='${hits} hits (${unique_hits} unique)'>
                    ${hits} views
                </span>
            % elif metric == 'date_created':
                <span class="badge" rel='tooltip' data-original-title='Created: ${explicit_date}'>
                    ${node.date_created.date()}
                </span>
            % endif
        <!-- <div class='project-authors'> -->
            % for index, user_id in enumerate(node.contributors[:3]):
                <%
                    if index == 2 and len(node.contributors) > 3:
                        # third item, > 3 total items
                        sep = ' & <a href="{url}">{num} other{plural}</a>'.format(
                            num=len(node.contributors) - 3,
                            plural='s' if len(node.contributors) - 3 else '',
                            url=node.url
                        )
                    elif index == len(node.contributors) - 1:
                        # last item
                        sep = ''
                    elif index == len(node.contributors) - 2:
                        # second to last item
                        sep = ' & '
                    else:
                        sep = ','
                %>
                ${print_user(user_id, format='surname')}${sep}
            % endfor
        <!-- </div> -->
    </li>
%endfor

</%def>

<%def name="print_user(user_id, format='long')">
<%
    user = get_user(user_id)
    name_formatters = {
        'long': lambda: user.fullname,
        'surname': lambda: user.surname,
        'initials': lambda: u'{surname}, {initial}.'.format(
            surname=user.surname,
            initial=user.given_name_initial
        ),
    }
    user_display_name = name_formatters[format]()
%>
<a class="list-group-item-text" rel='tooltip' href='/profile/${user_id}' data-original-title='${user.fullname}'>${user_display_name}</a></%def>
