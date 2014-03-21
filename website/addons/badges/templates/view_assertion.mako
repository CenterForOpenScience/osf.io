<link rel="stylesheet" href="/static/vendor/bower_components/bootstrap/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="/static/vendor/bower_components/bootstrap/dist/css/bootstrap-theme.min.css">
<script src="/static/vendor/bower_components/jQuery/dist/jquery.min.js"></script>
<script src="/addons/static/badges/png-baker.js"></script>
<br />
<div class="media well">
  <a class="pull-left" href="/badge/assertions/${uid}/json/">
    <img class="media-object" src="${image}" width="150px" height="150px" id="image">
  </a>
  <div class="media-body">
    <h3 class="media-heading"> <a href="${url}">${name}</a>
        <small> ${description} </small>
        <small class="pull-right">Endorsed by <a href="${issuer}">${issuer_name}</a></small>
        </h3>
    ${criteria} <br />
    <h4>Awarded to <a href="/${recipient['identity']}/">{project_name}</a><small> on ${issued_on}</small></h4>
  </div>
</div>

<script type="text/javascript">
 $('#image').load(function() {
  var c = document.createElement("canvas");
  c.width = 250;
  c.height= 250;
  var ctx = c.getContext("2d");
  var img = document.getElementById("image");
  //img.src = '${image}';
  ctx.drawImage(img, 0, 0, 250, 250);
  var baker = new PNGBaker(c.toDataURL());
  baker.textChunks['openbadges'] = JSON.stringify(${batter});
  var baked = URL.createObjectURL(baker.toBlob());
  console.log(baked);
  img.src = baked;
  $(this).unbind('load')
});
</script>
