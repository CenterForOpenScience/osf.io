$(document).ready(function(){
    $('#awardBadge').editable({
      name:  'title',
      title: 'Award Badge',
      display: false,
      highlight: false,
      placement: 'right',
      showbuttons: 'bottom',
      type: 'AwardBadge',
      value: '${badges[0]['id']}',
      badges: [
        %for badge in badges:
          {value: '${badge['id']}', text: '${badge['name']}'},
        %endfor
      ],
      ajaxOptions: {
        'type': 'POST',
        "dataType": "json",
        "contentType": "application/json"
      },
      url: nodeApiUrl + 'badges/award/',
      params: function(params){
        // Send JSON data
        return JSON.stringify(params.value);
      },
      success: function(data){
        document.location.reload(true);
      },
      pk: 'newBadge'
    });

    $('.revoke-badge').editable({
      type: 'text',
      pk: 'revoke',
      title: 'Revoke this badge?',
      placeholder: 'Reason',
      display: false,
      validate: function(value) {
        if($.trim(value) == '') return 'A reason is required';
      },
      ajaxOptions: {
        'type': 'POST',
        "dataType": "json",
        "contentType": "application/json"
      },
      url: nodeApiUrl + 'badges/revoke/',
      params: function(params){
        // Send JSON data
        var uid = $(this).attr('badge-uid')
        return JSON.stringify({reason: params.value, id: uid});
      },
      success: function(data){
        document.location.reload(true);
      },
    });
});
