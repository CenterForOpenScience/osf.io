<%inherit file="preprints/base.mako"/>
<%def name="title()">Explore Preprints</%def>
<%def name="content()">
<%
    from framework.auth import get_user
%>



##  <div class="row">
##    <div class="col-md-3">
##        <div data-spy="affix" class="sidebar affix hidden-print" role="complementary">
##            <ul class="nav nav-stacked nav-pills">
##                <li><a href="#newPreprints">Newest Preprints</a></li>
##                <li><a href='#popularPreprints'>Popular Preprints</a></li>
##            </ul>
##        </div><!-- end sidebar -->
##    </div>
##
##    <div class="col-md-9" role="main">
##      <h1 class="page-header">Public Preprint Activity</h1>
##        <section id='newPreprints'>
##            <h3>Newest Preprints</h3>
##            <ul class='project-list list-group'>
##                ${node_list(recent_preprints, prefix='newest_public', metric='date_created', url_suffix='preprint/')}
##            </ul>
##        </section>
##        <section id="popularPreprints">
##            <h3>Popular Preprints</h3>
##            <ul class='project-list list-group'>
##                ${node_list(popular_preprints, prefix='most_viewed', metric='hits')}
##            </ul>
##        </section>
##    </div>
##  </div><!-- /.row -->
<div class="panel-group" id="preprint-disciplines" data-bind="foreach: { data: disciplines, as: 'discipline' }">
    <div class="panel panel-default">
        <div class="panel-heading">
            <h4 class="panel-title">
                <a data-toggle="collapse" data-parent="#preprint-disciplines" href="#{{ discipline.topDisciplinceFormatted}}">{{discipline.topDisciplince}}</a>
            </h4>
        </div>
        <div id="{{ discipline.topDisciplinceFormatted}}" class="panel-collapse collapse">
            <div class="panel-body">
                <table data-bind="foreach: { data: discipline.children, as: 'subtopic' }" class="table table-striped">
                    <tr>
                        <td>{{ subtopic.readable }}</td>
                        <td><a href="/preprint/{{ discipline.topDisciplinceFormatted }}/{{ subtopic.stripped }}/newest/">Newest </a></td>
                        <td><a href="/preprint/{{ discipline.topDisciplinceFormatted }}/{{ subtopic.stripped }}/mostpopular/">Most Popular</a></td>
                        <td><a href="/preprint/{{ discipline.topDisciplinceFormatted }}/{{ subtopic.stripped }}/search/">Find more</a></td>
                    </tr>
                </table>
            </div>
        </div>
    </div>
</div>

<script src="/static/vendor/bower_components/bootstrap/js/transition.js"></script>
<script src="/static/vendor/bower_components/bootstrap/js/collapse.js"></script>
<script>
    $script('/static/js/preprintExplore.js', function() {
        PreprintModel('/api/v1/preprint/disciplines/', '#disciplines');
    });
</script>

</%def>
