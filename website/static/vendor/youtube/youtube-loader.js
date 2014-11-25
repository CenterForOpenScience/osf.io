(function () {
    'use strict';

    var players = document.getElementsByClassName('youtube-loader');

    if (players.length > 0) {
        var style = document.createElement('style');
        style.type = 'text/css';
        style.innerHTML =
            '.youtube-loader {' +
                'background-color:#000;' +
                'max-width:100%;' +
                'overflow:hidden;' +
                'position:relative;' +
                'cursor:hand;' +
                'cursor:pointer;' +
            '}' +
            '.youtube-loader .thumb {' +
                'bottom:0;' +
                'display:block;' +
                'left:0;' +
                'margin:auto;' +
                'max-width:100%;' +
                'position:absolute;' +
                'right:0;' +
                'top:0;' +
                'width:100%;' +
                'height:auto;' +
            '}' +
            '.youtube-loader .play {' +
                'transform:scale(0.858333333333333);' +
                'filter:alpha(opacity=80);' +
                'opacity:.9;' +
                'height:60px;' +
                'left:50%;' +
                'margin-left:-38px;' +
                'margin-top:-38px;' +
                'position:absolute;' +
                'top:50%;' +
                'width:85px;' +
                'background:url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFUAAAA8CAYAAAAXDvbIAAAEmklEQVR4Xu2cv0/bQBTHa0BC6pAiuiAlgFm6tYUOnSo1/AVNNjaoWEBCKl1AQkiFv4BEsDdsbKUSsIDUIHVOwgIjCSQVEyV0AgHp9zk5K7YT7GAn9tl3UiSM757vPvfu3buf0rMWQzgcHpUk6QVL1tXVNYq/+xqIkRFPtig+ajGeWbQcIlyZRapUKnnEoZ8+XD08PJAMJSBeuVQqqc9mctl7ySzi0NDQJODEEI/gWYVkJpa391QBOUDePjs72zTLfFOogPkFMOcDDLIZuyvATQDuarMIBqiyLPehCawB6JRZjQT8fRqM4vl83mBuNFAJKGrhV62pB5yZpeLnAHZcD1YDdXh4+AdEkf0UwTqBdKFQGK+PrkKNRCLR7u5u0lIRWiQAc/n5/Pw8Zej9oaUENNqiPBG9SiAPbR3RQB0YGJB7e3tPBaGnE7i7uxtjPq3S/OE+zcPgrj1dpEiJDj4JN4tc0GcM6jagfhJobBHIwQSMqVBhT//iodFQ09ZXgpYYUBUllYQ9da7q7+/vx4vFYloSrpRzUOFaxeFabUuDg4MxzDSR0y+CTQLorFbRWa1I6PlX0El9sylPJAcBAbUNagCoP6GpMdLUFDR1sg3fsCwyFApdI4QsJ/BuxEN4AFEJ7lQaefzoZj4zmczRxcXFv9nZ2RFkKuxmXmx+21tQ+/v731KBjo+Pf09MTLzhVHOVAYBnNJVBJbC0NrS7u5tdWlp6xxtcGgAQVJpIkW2qva3k1PzroTJhPMJlUCu2iDiQuBlUPdy5ubmoA59rqwhuoDIKmF4rJhKJ/MbGxoe2krEhnDuoPMDlFmo93OXl5T9bW1vvbSiXo0lvbm5GqKPyvE01K/Xl5WVuYWFBOjg4UNwyNwPNVPkCKoPoBbi+g1oPd3p6+nk2m33Vaa31LVQGcmdn5xBuWEeH4L6FCterlEwmT9fX1zvuevkOqpswWevwDVQMZ6/39vYymCsYK5fL6t7ZTttT+h73UL0Es853VmapuPNTvQiTQeVyRHVyckLzra/dbubNTAtXUAnmzMyMjExH3LCVVr/JoNJOYFeN+2NTf7zA1Df/NP7RUQdZX+uNoGLIeRSPx196XTP1ZWGa6imoBHNxcbGyv79Pp2F4C2BakD2zRkX0OIbJKr+6mop1f9e3UcKtK/LWzJs0IRWq2PbjnJERUJ1jWZVUv5dKbE13iK4KVexPdYhoVVO/YoNaQqJT0T09PVnnRAdXkrqTmhB4YVLFD1VBK6nYaJdXNv57YeefD6Aqjj+VQ5yjcqg2DeeoxAkV+2SZPVU1VZgA21DVpq+BilMqUzil8t22+AAKYP4pK7r+vH8aL1ydBuSwTjRaqtFUeqjZVrrdxtVJa47AlrEsHtXfCGS4Q6U2GEihYK5v9vI43CMAnWp0xVLD235ql9PQnAAdtRZaq6td2NBN9D/zjS6lMTR/vWYQXLgKMbqXCr9owAEXADN1e3ubolHTY63I9LIvfWKagAHgPvzqlzv0z/pkXun8CsiYAQhg0eKn5qY0/I8u91KuR6KT0a2YopahtiLcibhUiY3kUIGfcmWcE3kyk/EfxreyUB6zPb0AAAAASUVORK5CYII=") no-repeat' +
            '}' +
            '.youtube-loader img:hover + .play,' +
            '.youtube-loader .play:hover {' +
                'background:url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFUAAAA8CAYAAAAXDvbIAAAE+0lEQVR4Xu2czW8bRRTAZ7whREg1ViuIpdbGuXCjxMThhIRz5oDDpSfU8CF64IDLl1pxoP0DoCn8AbgHJG4NokXiQ2oq9YZbO4cWKkV0bad4A6K1XYlC8O7jzVq78q7t7NpePLveGSlSbM+8mfntmzdvZmceJUOm0hOHF0GijxvFNIgsUkpidjFAIIXfsT8XiWZdZHLMAkDKlELDMSMhMiVU7mkzkEaEamXje6pCM/3HXfOzC7l6FuqUsRhPHicAOULpontITlID97uMDMrIYCOjVC84tX4g1OJ88h1Eng8xyP7sUJtxZK4vKdWzg+D2QC3FYjF17sA5VOI1pycS7t9hU/r7wWq60egxNxaoDGj70egVfBJsqIvkQIDZ8Jl/Wit2sBaoxfnERbQbOUFzGAKwmVFqK90lTKg/xY9kKYlcGUacyNshQAm8tqTUCqbXYPxTjCcQqDeuTQhhy+gVLFigluLxlEpm74QQhmddllQ1bfi0+vC/Pp/MAyU444s0MgHQzmd2d5gL2nH+cYLawAnq5ZEFioK4NiDl5d1qugtq8j7i7VlqClbDEUC7qispFfZ0OHD75QairSwrO5tUuFLeQSUarGZ+r23Q4pOJHInQix6KDq0oIOTsslI9g5qaPIOG4OPQkvCw4wKqhzBNUQBfZ3ZrOYorqQLOV8f/jzrcypSi0ZbaakXd5vdrPtyYv7qs1LI4/BObuAv+Is+GHr1Z2mrXlQfbb55Y2JOrh3m2ZZy6fQf1kYMHn2Udenjz1rXbrxw7GkTNNRYAvtFUAyoDCwDNxqXLpcr7p58LGly2AECbmmQbKalx1H7csmz4d0M15AURrgEVPQG+aRBUO9xf33o7y7elzrUHBqoJt93eqX+yLtfXP3/BuXt8cgQOahDgBhZqN9zKqY9++/PLr57no5e9tUpkb4FNVL63qU7A/r13ryyf/IC2vv9Rd8t4JrZTNRVQDYh+gDt1ULvhbr/6+mN/3Sg9PWmtnVqoBsj731y6im7YRJfgUwsV2u279U/P36mf+2zirtfUQeUJ0/RIpmWiwuVsq3n52xvye6fTaqtpnp2dtD1l9QVeU/0E03iA7FBFIF0qP8I0oAZyRfXw1s/Xbq8ee4b3MB9kWgIFlcHcfuNEak+uHOFhK93W2YE6n2zg6RSuxn2/rb+gwLQMf7+8o7JvUuOSc+uXl3KH/K6Zdg3WNdVvUBnMyrsfQvO7H4J4RL6CUFO+gcqeeIBh6gprvk31wzHK2dRTO0Eb5v0mrq5X1OLYj9uZ3SmfgOpEaITfzbNU4mj6CPQGFOk6oCau+niFlQI5ubRbXafsVrQqSSWvBIdZjnmSmkHww8u/aXgY7E1qWlHw2jsmPywApgCq7vizfoh7VF49Tfs9KnFDZXyyhj01NVWYgLGhmkPfAvV6PLEGhH4xtvgQCjD8U6Prlvv+YsIaSSMsWmrRVPZBt60wiwFY+G5aj9Q1HoWANCVNzdojAvXGUGGLgUikgBeAuR/24sHJdZ0AW5KmrfULsdQ32o8eS2UumsdlV15obT/McAGD0uT7BaXpGf724gyuNncgh7cuMK4KRq0It1mo4IRUmCF7BbZq2k+jHYN92QvrF4Q1GoOIHvxLTxS0GHSCgfVNvO9pdTUKwUAPEByRDWy/JVIa1aAMkU40NnYz2rVZYDyGycwjL3uI/eqdUaExSsi4SfThP5yCtWKJCDx6AAAAAElFTkSuQmCC") no-repeat' +
            '}';
        document.body.appendChild(style);
    }

    var onClick = function () {
        var iframe = document.createElement('iframe');
        iframe.className = this.className.replace('youtube-loader', 'youtube-loader-embedded');
        var src = '//www.youtube.com/embed/' + this.id + '?autoplay=1&autohide=1&border=0&wmode=opaque&enablejsapi=1&hd=1&showinfo=0';
        var start = this.getAttribute('start');
        if (start) {
            src += '&start=' + start
        }
        iframe.setAttribute('src', src);
        iframe.setAttribute('allowfullscreen', '');
        iframe.setAttribute('frameborder', '0');
        iframe.setAttribute('type', 'text/html');
        this.parentNode.replaceChild(iframe, this);
    };

    for (var i = 0; i < players.length; i++) {
        var player = players[i];

        var img = document.createElement('img');
        img.setAttribute('src', '//i.ytimg.com/vi/' + player.id + '/maxresdefault.jpg');
        img.setAttribute('class', 'thumb');

        var div = document.createElement('div');
        div.setAttribute('class', 'play');

        player.appendChild(img);
        player.appendChild(div);

        player.onclick = onClick;
    }
})();
