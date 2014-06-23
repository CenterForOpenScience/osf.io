<%inherit file="project/addon/widget.mako"/>

<div id="dataverseScope" class="scripted">

    <span data-bind="if: loaded">
        <dl class="dl-horizontal dl-dataverse" style="white-space: normal">

            <dt>Study</dt>
            <dd>{{ study }}</dd>

            <dt>Global ID</dt>
            <dd><a data-bind="attr: {href: studyUrl}">{{ doi }}</a></dd>

            <dt>Dataverse</dt>
            <dd><a data-bind="attr: {href: dataverseUrl}">{{ dataverse }}</a></dd>

            <dt>Citation</dt>
            <dd>{{ citation }}</dd>

        </dl>
    </span>

</div>

<script>
    $script(['/static/addons/dataverse/dataverseWidget.js']);
    $script.ready('dataverseWidget', function() {
        var url = '${node['api_url'] + 'dataverse/widget/contents/'}';
        var dataverse = new DataverseWidget('#dataverseScope', url);
    });
</script>
