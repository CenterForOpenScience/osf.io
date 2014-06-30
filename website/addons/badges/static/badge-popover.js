$('.badge-popover').popover({
  container: 'body',
  trigger: 'click',
  html: true,
  placement: 'auto'
});

$('.badge-popover').on('show.bs.popover', function () {
  var self = this;
  $('.badge-popover').each(function(id, popover) {
    $(popover).not(self).popover('hide');
  });
});
