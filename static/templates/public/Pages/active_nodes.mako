<%inherit file="contentContainer.mako" />

<%
    from framework import get_user
%>

<style type='text/css'>
    ul#sideNav {
        width: 280px;
        position:fixed;
    }
    ul.project-list {
        margin-left:0;
        margin-top:15px;
    }
    ul.project-list div.body {overflow:hidden;}
    ul.project-list td ul {margin:0}
    ul.project-list td li {list-style-type:none}
    ul.project-list table.table {margin-bottom:0;}
    ul.project-list table.table th {width:100px;}
    ul.project-list div.project-authors{
        border-bottom-left-radius: 6px;
        border-bottom-right-radius: 6px;
        background-color:white;
        padding: 0 10px 10px 10px;
        font-style:italic;
    }
    ul.project-list h3 {
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;
        padding-bottom:0;
        line-height:18px;
    }
    ul.project-list h3 a {
        display:block;
        padding-right:110px;
    }
    ul.project-list div.project-meta {
        position: absolute;
        top: 10px;
        right: 10px;
        font-weight: normal;
        font-style: italic;
    }
    ul.project-list li.project { position:relative }
</style>
<script>
$(function(){
    // This makes sure that links clicked on the sidebar account for the height of the header.
    var offset = 50;

    $('#sideNav li a').click(function(event) {
        event.preventDefault();
        $($(this).attr('href'))[0].scrollIntoView();
        scrollBy(0, -offset);
    });
})
</script>

<div class='row'>
    <div class='span4' style='height:1px'>
        <ul id='sideNav' class='nav nav-stacked nav-tabs'>
            <li><a href='#newPublicProjects'>Newest Public Projects</a></li>
            <li><a href='#newPublicRegistrations'>Newest Public Registrations</a></li>
            <li><a href='#popularPublicProjects'>Most Viewed Public Projects</a></li>
            <li><a href='#popularPublicRegistrations'>Most Viewed Public Registrations</a></li>
        </ul>
    </div>
    <div class='span8'>
        <section id='newPublicProjects'>
            <h2>Newest Public Projects</h2>
            <ul class='project-list'>
                ${node_list(recent_public_projects, prefix='newest_public', metric='date_created')}
            </ul>
        </section>
        <section id='newPublicRegistrations'>
            <h2>Newest Public Registrations</h2>
            <ul class='project-list'>
                ${node_list(recent_public_registrations, prefix='newest_public', metric='date_created')}
            </ul>
        </section>
        <section id='popularPublicProjects'>
            <h2>Most Viewed Public Projects</h2>
            <ul class='project-list'>
                ${node_list(most_viewed_projects, prefix='most_viewed')}
            </ul>
        </section>
        <section id='popularPublicRegistrations'>
            <h2>Most Viewed Public Registrations</h2>
            <ul class='project-list'>
                ${node_list(most_viewed_registrations, prefix='most_viewed')}
            </ul>
        </section>
    </div>
</div>

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
    <li class="project">
        <h3>
            <a href="${node.url}">${node.title}</a>
        </h3>
        <div class='project-meta'>
            % if metric == 'hits':
                <a rel='tooltip' data-original-title='${hits} hits <br>${unique_hits} unique'>
                    ${hits}
                </a>
            % elif metric == 'date_created':
                <a rel='tooltip' data-original-title='Created: ${explicit_date}'>
                    ${node.date_created.date()}
                </a>
            % endif
        </div>

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