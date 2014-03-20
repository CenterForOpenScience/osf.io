<%inherit file="project/addon/widget.mako"/>

%if can_issue and configured:
<button class="btn btn-success pull-right" id="awardBadge">
<!-- TODO Change to awesomefont -->
    <span class="glyphicon glyphicon-plus" />
</button>
%endif

<div style="max-height:200px; overflow-y: auto; overflow-x: hidden;">
    <ul class="media-list" id="badgeList" style="columns: 2;-webkit-columns: 2;-moz-columns: 2;">
        %for assertion in assertions:
        <li class="media well well-sm">
          <a class="pull-left" href="/${assertion['uid']}/">
            <img class="media-object" src="${assertion['image']}" width="64px" height="64px">
          </a>
            <h5>${assertion['name']}</h5>
            ${assertion['criteria']}
        </li>
        %endfor
    </ul>
</div>
<script>

$('#awardBadge').click(function() {
  $.ajax({
    url: nodeApiUrl + 'badges/award/',
    method: 'POST',
    dataType: 'json',
    contentType: 'application/json',
    data: JSON.stringify({badgeid: '${badges[2]['id']}'})
  })
})
</script>

