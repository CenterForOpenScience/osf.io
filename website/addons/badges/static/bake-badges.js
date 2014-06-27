$script('/static/addons/badges/png-baker.js', function() {
    var canvas = document.createElement("canvas");

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

    var beginBake = function(badge) {
        if ($(badge).attr('badge-url')) {
            $.ajax({
                method: 'get',
                url: $(badge).attr('badge-url'),
                success: function(rv) {
                    bakeBadge(badge, rv)
                    $(badge).unbind('load');
                }
            });
        }
    };

    $('.open-badge').each(function() {
        var self = this;
        if (this.complete) {
            beginBake(self);
        } else {
            $(this).load(function() {
                beginBake(this);
            });
        }
    });

});
