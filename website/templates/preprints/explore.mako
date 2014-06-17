<%inherit file="base.mako"/>
<%def name="title()">Explore Preprints</%def>
<%def name="content()">
<%
    from framework.auth import get_user
%>
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
