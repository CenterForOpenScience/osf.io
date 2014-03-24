var canvas = document.createElement("canvas");

$(document).ready(function() {
    $('.open-badge').each(function() {
        $(this).load(function() {
            var badge = this
            $.ajax({
                method: 'get',
                url: $(this).attr('badge-url'),
                success: function(rv) {
                    bakeBadge(badge, rv)
                    $(badge).unbind('load');
                }
            })
        });
    });
});

var bakeBadge = function(img, metadata) {
    canvas.width = 250;
    canvas.height = 250;
    var ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0, 250, 250);
    var baker = new PNGBaker(canvas.toDataURL());
    baker.textChunks['openbadges'] = JSON.stringify(metadata);
    var baked = URL.createObjectURL(baker.toBlob());
    img.src = baked;
};
