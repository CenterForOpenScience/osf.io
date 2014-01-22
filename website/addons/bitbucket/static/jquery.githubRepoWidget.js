;jQuery(document).ready(function($){

	var i = 0;
	var box_title_png = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAXCAMAAAAx3e/WAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAyRpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuMC1jMDYxIDY0LjE0MDk0OSwgMjAxMC8xMi8wNy0xMDo1NzowMSAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENTNS4xIE1hY2ludG9zaCIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDpEQjIyNkJERkM0NjYxMUUxOEFDQzk3ODcxRDkzRjhCRSIgeG1wTU06RG9jdW1lbnRJRD0ieG1wLmRpZDpEQjIyNkJFMEM0NjYxMUUxOEFDQzk3ODcxRDkzRjhCRSI+IDx4bXBNTTpEZXJpdmVkRnJvbSBzdFJlZjppbnN0YW5jZUlEPSJ4bXAuaWlkOkRCMjI2QkREQzQ2NjExRTE4QUNDOTc4NzFEOTNGOEJFIiBzdFJlZjpkb2N1bWVudElEPSJ4bXAuZGlkOkRCMjI2QkRFQzQ2NjExRTE4QUNDOTc4NzFEOTNGOEJFIi8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+dka2KgAAAEVQTFRFxMTEyMjI0tLSvb29vr6+zc3Ny8vLxcXFz8/P6enp3t7ex8fH0dHR1NTUw8PDwMDAzs7OvLy8wcHBu7u7v7+/zMzM////budQFwAAABd0Uk5T/////////////////////////////wDmQOZeAAAAcklEQVR42tSQSQ7DMAwD6chOukWs5eX/Ty2coo0T9wOdEzEgdRBuzNmnDofgja52JDyz5TCqUp0O6kfrb4bzSXkRiTviEZZ6JKLMJ5VQ2v8iGbtbfEwXmjFMG0VwdQo10hQNxYqtLMv9O6xvpZ/QeAkwAKjwHiJLaJc3AAAAAElFTkSuQmCC';
	var stats_png = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAqCAMAAACEJ4viAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAyRpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuMC1jMDYxIDY0LjE0MDk0OSwgMjAxMC8xMi8wNy0xMDo1NzowMSAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENTNS4xIE1hY2ludG9zaCIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDpEQjIyNkJEQkM0NjYxMUUxOEFDQzk3ODcxRDkzRjhCRSIgeG1wTU06RG9jdW1lbnRJRD0ieG1wLmRpZDpEQjIyNkJEQ0M0NjYxMUUxOEFDQzk3ODcxRDkzRjhCRSI+IDx4bXBNTTpEZXJpdmVkRnJvbSBzdFJlZjppbnN0YW5jZUlEPSJ4bXAuaWlkOkRCMjI2QkQ5QzQ2NjExRTE4QUNDOTc4NzFEOTNGOEJFIiBzdFJlZjpkb2N1bWVudElEPSJ4bXAuZGlkOkRCMjI2QkRBQzQ2NjExRTE4QUNDOTc4NzFEOTNGOEJFIi8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+h1kA9gAAAK5QTFRF+fn5sbGx8fHx09PTmpqa2dnZ/f3919fX9PT00NDQ1dXVpKSk+vr6+/v7vb298vLyycnJ8/PztLS0zc3N6enp/v7+q6ur2NjY9/f3srKy/Pz8p6en7u7uoaGhnJyc4eHhtbW1pqam6Ojo9fX17e3toqKirKys1NTUzs7Ox8fHwcHBwMDA5eXlnZ2dpaWl0dHR9vb25ubm4uLi3d3dqqqqwsLCv7+/oKCgmZmZ////8yEsbwAAAMBJREFUeNrE0tcOgjAUBuDSliUoMhTEvfdef9//xUQjgaLX0Ium/ZLT/+SkRPxZpGykvuf5VMJogy5jY9yjDHcWFhqlcRuHc4o6B1QK0BDg+hcZgNDh3NWTwzItH/bRrhvT+g3zSxZkNGCZpoWGIbU0a3Y6zV5VA6keyeDxiw62P0gUqEW0FbDim4nVikFJbU2zZXybUEaxhCqOQqyh5/G0wpWICUwthyqwD4InOMuXJ7/gs7WkoPdVg1vykF8CDACEFanKO3aSYwAAAABJRU5ErkJggg==';


	$('.github-widget').each(function(){

        var that = this;

		if(i == 0) $('head').append(
			'<style type="text/css">'
			+'.github-box *{-webkit-box-sizing:content-box;-moz-box-sizing:content-box;box-sizing:content-box;}'
			+'.github-box{font-family:helvetica,arial,sans-serif;font-size:13px;line-height:18px;background:#fafafa;border:1px solid #ddd;color:#666;border-radius:3px}'
			+'.github-box a{color:#4183c4;border:0;text-decoration:none}'
			+'.github-box .github-box-title{position:relative;border-bottom:1px solid #ddd;border-radius:3px 3px 0 0;background:#fcfcfc;background:-moz-linear-gradient(#fcfcfc,#ebebeb);background:-webkit-linear-gradient(#fcfcfc,#ebebeb);}'
			+'.github-box .github-box-title h3{word-wrap:break-word;font-family:helvetica,arial,sans-serif;font-weight:normal;font-size:16px;color:gray;margin:0;padding:10px 10px 10px 30px;background:url('+box_title_png+') 7px center no-repeat; width: auto;}'
			+'.github-box .github-box-title h3 .repo{font-weight:bold}'
			+'.github-box .github-box-title .github-stats{float:right;position:absolute;top:8px;right:10px;font-size:11px;font-weight:bold;line-height:21px;height:auto;min-height:21px}'
			+'.github-box .github-box-title .github-stats a{display:inline-block;height:21px;color:#666;border:1px solid #ddd;border-radius:3px;padding:0 5px 0 18px;background: white url('+stats_png+') no-repeat}'
			+'.github-box .github-box-title .github-stats .watchers{border-right:1px solid #ddd}'
			+'.github-box .github-box-title .github-stats .forks{background-position:-4px -21px;padding-left:15px}'
			+'.github-box .github-box-content{padding:10px;font-weight:300}'
			+'.github-box .github-box-content p{margin:0}'
			+'.github-box .github-box-content .link{font-weight:bold}'
			+'.github-box .github-box-download{position:relative;border-top:1px solid #ddd;background:white;border-radius:0 0 3px 3px;padding:10px;height:auto;min-height:24px;}'
			+'.github-box .github-box-download .updated{word-wrap:break-word;margin:0;font-size:11px;color:#666;line-height:24px;font-weight:300;width:auto}'
			+'.github-box .github-box-download .updated strong{font-weight:bold;color:#000}'
			+'.github-box .github-box-download .download{float:right;position:absolute;top:10px;right:10px;height:24px;line-height:24px;font-size:12px;color:#666;font-weight:bold;text-shadow:0 1px 0 rgba(255,255,255,0.9);padding:0 10px;border:1px solid #ddd;border-bottom-color:#bbb;border-radius:3px;background:#f5f5f5;background:-moz-linear-gradient(#f5f5f5,#e5e5e5);background:-webkit-linear-gradient(#f5f5f5,#e5e5e5);}'
			+'.github-box .github-box-download .download:hover{color:#527894;border-color:#cfe3ed;border-bottom-color:#9fc7db;background:#f1f7fa;background:-moz-linear-gradient(#f1f7fa,#dbeaf1);background:-webkit-linear-gradient(#f1f7fa,#dbeaf1);}'
			+'@media (max-width: 767px) {'
			+'.github-box .github-box-title{height:auto;min-height:60px}'
			+'.github-box .github-box-title h3 .repo{display:block}'
			+'.github-box .github-box-title .github-stats a{display:block;clear:right;float:right;}'
			+'.github-box .github-box-download{height:auto;min-height:46px;}'
			+'.github-box .github-box-download .download{top:32px;}'
			+'}'
			+'</style>'
		);
		i++;

		var $container = $(this), $widget,
			repo = $container.data('repo'),
			vendorName = repo.split('/')[0],
			repoName = repo.split('/')[1],
			vendorUrl = "http://github.com/" + vendorName,
			repoUrl = "http://github.com/" + vendorName + '/' + repoName;

		$widget = $(
			'<div class="github-box repo">'
			+'<div class="github-box-title">'
			+'<h3>'
			+'<a class="owner" href="' + vendorUrl + '" title="' + vendorUrl + '">' + vendorName + '</a>'
			+'/'
			+'<a class="repo" href="' + repoUrl + '" title="' + repoUrl + '">' + repoName + '</a>'
			+'</h3>'
			+'<div class="github-stats">'
			+'<a class="watchers" href="' + repoUrl + '/watchers" title="See watchers">?</a>'
			+'<a class="forks" href="' + repoUrl + '/network/members" title="See forkers">?</a>'
			+'</div>'
			+'</div>'
			+'<div class="github-box-download">'
			+'<div class="updated"></div>'
			+'<a class="download" href="' + nodeApiUrl + 'github/zipball/" title="Get an archive of this repository">Download as zip</a>'
			+'</div>'
			+'</div>'
		);

		$widget.appendTo($container);

		$.ajax({
			url: nodeApiUrl + 'github/',
            contentType: 'application/json',
			dataType: 'json',
			success: function(results) {
				var repo = results.data, date, pushed_at = 'unknown';

				if (repo.pushed_at) {
					date = new Date(repo.pushed_at);
					pushed_at = (date.getMonth() + 1) + '-' + date.getDate() + '-' + date.getFullYear();
				}

				$widget.find('.watchers').text(repo.watchers);
				$widget.find('.forks').text(repo.forks);
				$widget.find('.description span').text(repo.description);
				$widget.find('.updated').html('Latest commit to the <strong>' + repo.default_branch + '</strong> branch on ' + pushed_at);

				// Don't show "null" if the repo has no homepage URL.
				if(repo.homepage != null) $widget.find('.link').append($('<a />').attr('href', repo.homepage).text(repo.homepage));

                // Open foreign links in new tab or window
                $(that).find('a[href*="github.com"]').attr('target', '_blank');
			}
		});

	});

});