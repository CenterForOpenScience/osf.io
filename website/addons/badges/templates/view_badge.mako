<%inherit file="base.mako"/>

<%def name="title()">${badge.name}</%def>

<%def name="content()">

<div class="media well">
  %if badge.is_system_badge:
    <span class="pull-right" style="text-align:end;">System Badge
  %else:
    <span class="pull-right" style="text-align:end;">Endorsed by <a href="${badge.creator.owner.profile_url}">${badge.creator.owner.fullname}</a>
  %endif
  <br/>
  Awarded ${badge.awarded_count} Times to ${badge.unique_awards_count} Projects</span>
  <a class="pull-left">
    <img class="media-object" src="${badge.image}" width="150px" height="150px">
  </a>
  <div class="media-body">
    <h4 class="media-heading">${badge.name}
        <small> ${badge.description} </small>
        </h4>
    ${badge.criteria_list}
  </div>
</div>

<div class="hgrid" id="grid" width="100%"></div>

</%def>

<%def name="javascript_bottom()">
<!-- <script src="/static/vendor/hgrid/hgrid.js"></script>
<script src="/static/vendor/dropzone/dropzone.js"></script> -->
<script>
$script.ready('hgrid', function() {
    // TODO: Rewrite substantially before reactivating addon
    var data = [
      %for assertion in assertions:
        %if not assertion.revoked:
          {
            name: '<a href="${assertion.node.absolute_url}">${assertion.node.title}</a>',
            description: '${assertion.node.description or 'No description'}',
            date: '${assertion.issued_date}',
            evidence: '${'<a href="' + assertion.evidence + '">' + assertion.evidence + '</a>' if assertion.evidence else 'None provided'}',
            %if badge.is_system_badge:
              awarder: '<a href="${assertion.awarder.owner.profile_url}">${assertion.awarder.owner.fullname}</a>',
            %endif
            kind: 'item',
            //children: [],
          },
        %endif
      %endfor
    ];

    HGrid.Col.Name.text = 'Project Name';
    HGrid.Col.Name.itemView = '{{ name }}';
    var dateColumn = {
      text: 'Awarded on',
      itemView: '{{ date }}',
      sortable: true,
      sortkey: 'date', // property of item object on which to sort on
    };
    var descriptionColumn = {
      text: 'Description',
      itemView: '{{ description }}',
      sortable: true,
      sortkey: 'description', // property of item object on which to sort on
    };
    var evidenceColumn = {
      text: 'Evidence',
      itemView: '{{ evidence }}',
      sortable: true,
      sortkey: 'evidence', // property of item object on which to sort on
    };
    %if badge.is_system_badge:
      var awarderColumn = {
        text: 'Awarder',
        itemView: '{{ awarder }}',
        sortable: true,
        sortkey: 'awarder', // property of item object on which to sort on
      };
    %endif
    var grid = new HGrid('#grid', {
      columns: [
        HGrid.Col.Name,
        descriptionColumn,
        dateColumn,
        %if badge.is_system_badge:
          awarderColumn,
        %endif
        evidenceColumn
      ],
      data: data,
      width: '100%'
    });
});
</script>
</%def>
