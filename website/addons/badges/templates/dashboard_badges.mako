%if len(badges) < 1:
You have not created any Badges.
%endif
  <div style="max-height:300px;overflow:auto;">
    <ul class="media-list" id="badgeList">
        %for badge in badges:
        <li class="media">
          <a class="pull-left" href="/${badge._id}/">
            <img class="media-object" src="${badge.image}" width="64px" height="64px">
          </a>
          <div class="media-body">
            <h4 class="media-heading">${badge.name}<small> ${badge.description} </small></h4>
            ${badge.criteria_list}
          </div>
        </li>
        %endfor
    </ul>
  </div>

<script type="text/javascript">
//TODO Make bootbox into a form? [with submit]
//TODO Image uploading
    $(document).ready(function() {
        $('#newBadge').click(function(){
            bootbox.dialog({
                // TODO: Rewrite substantially before reactivating addon
              message: '<form id="badgeForm">' +
              '<input type="text" class="form-control" name="badgeName" placeholder="Badge Name"><br />' +
              '<input type="text" class="form-control" name="description" placeholder="Description"><br />' +
              '<input type="url" class="form-control" name="imageurl" placeholder="Image URL"><br />' +
              '<textarea class="form-control" name="criteria" placeholder="Criteria" />' +
              '</form>',
              title: 'Create a new badge',
              buttons: {
                submit: {
                  label: "Save",
                  className: "btn-success",
                  callback: function() {
                    var data = AddonHelper.formToObj('#badgeForm');
                    if(notEmpty(data)) {
                      $.ajax({
                        url: '/api/v1/badges/new/',
                        type: 'POST',
                        dataType: 'json',
                        contentType: 'application/json',
                        data: JSON.stringify(data),
                        success: function(response) {
                          %if len(badges) > 0:
                            $("#badgeList").append(jsonToList(data, response.badgeid));
                          %else:
                            document.location.reload(true);
                          %endif
                        },
                        error: function(xhr) {
                          alert('Failed: ' + xhr.statusText);
                        }
                      });
                    }
                  else {
                  alert('All fields must be filled out.')
                  return false;
                }
                  }
                },
                cancel: {
                  label: "Cancel",
                  className: "btn-default"
                }
              }
            });
        });
    });

  var notEmpty = function(list) {
    for(var key in list) {
      if(list[key].trim() === "")
        return false;
    }
    return true;
  };

//todo fetch url from server
  var jsonToList = function(badge, id) {
    return '<li class="media">' +
          '<a class="pull-left" href="/' + id + '/">' +
            '<img class="media-object" src="' + badge['imageurl'] + '" width="64px" height="64px"> </a>' +
                  '<div class="media-body">' +
                    '<h4 class="media-heading">' + badge['badgeName'] + '<small> ' + badge['description'] + '</small></h4>' +
        badge['criteria'] +
      '</div>' +
    '</li>'
  };

</script>
