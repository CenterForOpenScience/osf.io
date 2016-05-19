#
# This is an example VCL file for Varnish.
#
# It does not do anything by default, delegating control to the
# builtin VCL. The builtin VCL is called when there is no explicit
# return statement.
#
# See the VCL chapters in the Users Guide at https://www.varnish-cache.org/docs/
# and http://varnish-cache.org/trac/wiki/VCLExamples for more examples.

# Based on https://github.com/mattiasgeniar/varnish-4.0-configuration-templates/blob/master/default.vcl

# Marker to tell the VCL compiler that this VCL has been adapted to the
# new 4.0 format.
vcl 4.0;

import std;
import directors;

# Default backend definition. Set this to point to your content server.
backend server1 {
    .host = "127.0.0.1";
    .port = "8000";
	.max_connections = 1000; # That's it

	# .probe = {
 #    	#.url = "/"; # short easy way (GET /)
 #    	# We prefer to only do a HEAD /
 #    	.request =
 #      		"HEAD /v2/nodes/ HTTP/1.1"
 #      		"Host: localhost"
 #      		"Connection: close";

	# 	.interval  = 5s; # check the health of each backend every 5 seconds
 #    	.timeout   = 1s; # timing out after 1 second.
 #    	.window    = 5;  # If 3 out of the last 5 polls succeeded the backend is considered healthy, otherwise it will be marked as sick
 #    	.threshold = 3;
 #  	}

	.first_byte_timeout     = 300s;   # How long to wait before we receive a first byte from our backend?
	.connect_timeout        = 5s;     # How long to wait for a backend connection?
	.between_bytes_timeout  = 2s;     # How long to wait between bytes received from our backend?
}

# backend server2 {
#     .host = "127.0.0.1";
#     .port = "8100";
# 	.max_connections = 1000; # That's it

# 	# .probe = {
#  #    	#.url = "/"; # short easy way (GET /)
#  #    	# We prefer to only do a HEAD /
#  #    	.request =
#  #      		"HEAD /v2/nodes/ HTTP/1.1"
#  #      		"Host: localhost"
#  #      		"Connection: close";

# 	# 	.interval  = 5s; # check the health of each backend every 5 seconds
#  #    	.timeout   = 1s; # timing out after 1 second.
#  #    	.window    = 5;  # If 3 out of the last 5 polls succeeded the backend is considered healthy, otherwise it will be marked as sick
#  #    	.threshold = 3;
#  #  	}

# 	.first_byte_timeout     = 300s;   # How long to wait before we receive a first byte from our backend?
# 	.connect_timeout        = 5s;     # How long to wait for a backend connection?
# 	.between_bytes_timeout  = 2s;     # How long to wait between bytes received from our backend?
# }

# backend server3 {
#     .host = "127.0.0.1";
#     .port = "8100";
# 	.max_connections = 1000; # That's it

# 	# .probe = {
#  #    	#.url = "/"; # short easy way (GET /)
#  #    	# We prefer to only do a HEAD /
#  #    	.request =
#  #      		"HEAD /v2/nodes/ HTTP/1.1"
#  #      		"Host: localhost"
#  #      		"Connection: close";

# 	# 	.interval  = 5s; # check the health of each backend every 5 seconds
#  #    	.timeout   = 1s; # timing out after 1 second.
#  #    	.window    = 5;  # If 3 out of the last 5 polls succeeded the backend is considered healthy, otherwise it will be marked as sick
#  #    	.threshold = 3;
#  #  	}

# 	.first_byte_timeout     = 300s;   # How long to wait before we receive a first byte from our backend?
# 	.connect_timeout        = 5s;     # How long to wait for a backend connection?
# 	.between_bytes_timeout  = 2s;     # How long to wait between bytes received from our backend?
# }

acl purge {
  # ACL we'll use later to allow purges
  # We should add COS office and server ip ranges here
  "localhost";
  "127.0.0.1";
  "::1";
}

sub vcl_init {
  # Called when VCL is loaded, before any requests pass through it.
  # Typically used to initialize VMODs.

  new vdir = directors.round_robin();
  vdir.add_backend(server1);
  # vdir.add_backend(server2);
  # vdir.add_backend(server3);
}

sub vcl_purge {
	return(synth(200, "Purged Successfully"));
}

sub vcl_synth {
	if (req.method == "BAN" || req.method == "PURGE") {
		synthetic(resp.reason+{"
		"});
		call fix_headers;
		return(deliver);
	}
}

sub vcl_recv {
    # Happens before we check if we have this in cache already.
    #
    # Typically you clean up the request here, removing cookies you don't need,
    # rewriting the request, etc.

    set req.backend_hint = vdir.backend(); # send all traffic to the vdir director

	# Normalize the query arguments
  	set req.url = std.querysort(req.url);

  	# Allow purging
	if (req.method == "PURGE") {
		if (!client.ip ~ purge) { # purge is the ACL defined at the begining
			# Not from an allowed IP? Then die with an error.
			return (synth(405, "This IP is not allowed to send PURGE requests."));
		}
		# If you got this stage (and didn't error out above), purge the cached result
		return (purge);
	}

	if (req.method == "BAN") {
		if (!client.ip ~ purge) {
			return(synth(405, "This IP is not allowed to send BAN requests."));
		}
		# help background lurker to remove matching objects
		ban("obj.http.x-url ~ " + req.url);
		return(synth(200, "BAN by URL regex: " + req.url));
	}

  	# No SPDY
    if (req.method == "PRI") {
    	return (synth(405));
    }

	# Only deal with "normal" types
	if (req.method != "GET" &&
		req.method != "HEAD" &&
		req.method != "PUT" &&
		req.method != "POST" &&
		req.method != "TRACE" &&
		req.method != "OPTIONS" &&
		req.method != "PATCH" &&
		req.method != "DELETE") {
		/* Non-RFC2616 or CONNECT which is weird. */
		return (pipe);
	}

	# Only cache GET or HEAD requests. This makes sure the POST requests are always passed.
	# TODO: should we just be caching application/vnd.api+json? If so, here's where you do it.
	# filtering by v2 to make sure we only get api for now
	if (req.method != "GET" && req.method != "HEAD" && req.url ~ "^/v2/") {
		return (pass);
	}
	# Some generic URL manipulation, useful for all templates that follow
	# First remove the Google Analytics added parameters, useless for our backend
	if (req.url ~ "(\?|&)(utm_source|utm_medium|utm_campaign|utm_content|gclid|cx|ie|cof|siteurl)=") {
		set req.url = regsuball(req.url, "&(utm_source|utm_medium|utm_campaign|utm_content|gclid|cx|ie|cof|siteurl)=([A-z0-9_\-\.%25]+)", "");
		set req.url = regsuball(req.url, "\?(utm_source|utm_medium|utm_campaign|utm_content|gclid|cx|ie|cof|siteurl)=([A-z0-9_\-\.%25]+)", "?");
		set req.url = regsub(req.url, "\?&", "?");
		set req.url = regsub(req.url, "\?$", "");
	}

	# Strip hash, server doesn't need it.
	if (req.url ~ "\#") {
		set req.url = regsub(req.url, "\#.*$", "");
	}

	# Strip a trailing ? if it exists
	if (req.url ~ "\?$") {
		set req.url = regsub(req.url, "\?$", "");
	}

	# Some generic cookie manipulation, useful for all templates that follow
	# Remove the "has_js" cookie
	set req.http.Cookie = regsuball(req.http.Cookie, "has_js=[^;]+(; )?", "");

	# Remove any Google Analytics based cookies
	set req.http.Cookie = regsuball(req.http.Cookie, "__utm.=[^;]+(; )?", "");
	set req.http.Cookie = regsuball(req.http.Cookie, "_ga=[^;]+(; )?", "");
	set req.http.Cookie = regsuball(req.http.Cookie, "_gat=[^;]+(; )?", "");
	set req.http.Cookie = regsuball(req.http.Cookie, "utmctr=[^;]+(; )?", "");
	set req.http.Cookie = regsuball(req.http.Cookie, "utmcmd.=[^;]+(; )?", "");
	set req.http.Cookie = regsuball(req.http.Cookie, "utmccn.=[^;]+(; )?", "");

	# Remove DoubleClick offensive cookies
	set req.http.Cookie = regsuball(req.http.Cookie, "__gads=[^;]+(; )?", "");

	# Remove the Quant Capital cookies (added by some plugin, all __qca)
	set req.http.Cookie = regsuball(req.http.Cookie, "__qc.=[^;]+(; )?", "");

	# Remove the AddThis cookies
	set req.http.Cookie = regsuball(req.http.Cookie, "__atuv.=[^;]+(; )?", "");

    # Remove the csrf cookie
    set req.http.Cookie = regsuball(req.http.Cookie, "csrftoken=[^;]+(; )?", "");

	# Remove a ";" prefix in the cookie if present
	set req.http.Cookie = regsuball(req.http.Cookie, "^;\s*", "");

	# Are there cookies left with only spaces or that are empty?
	if (req.http.cookie ~ "^\s*$") {
		unset req.http.cookie;
	}

	# Large static files are delivered directly to the end-user without
	# waiting for Varnish to fully read the file first.
	# Varnish 4 fully supports Streaming, so set do_stream in vcl_backend_response()
	if (req.url ~ "^[^?]*\.(mp[34]|rar|tar|tgz|gz|wav|zip|bz2|xz|7z|avi|mov|ogm|mpe?g|mk[av]|webm)(\?.*)?$") {
		unset req.http.Cookie;
		return (hash);
	}

	# Remove all cookies for static files
	# A valid discussion could be held on this line: do you really need to cache static files that don't cause load? Only if you have memory left.
	# Sure, there's disk I/O, but chances are your OS will already have these files in their buffers (thus memory).
	# Before you blindly enable this, have a read here: https://ma.ttias.be/stop-caching-static-files/
	# if (req.url ~ "^[^?]*\.(bmp|bz2|css|doc|eot|flv|gif|gz|ico|jpeg|jpg|js|less|pdf|png|rtf|swf|txt|woff|xml)(\?.*)?$") {
	# 	unset req.http.Cookie;
	# 	return (hash);
	# }

	return (hash);
}

# The data on which the hashing will take place
sub vcl_hash {
  # Called after vcl_recv to create a hash value for the request. This is used as a key
  # to look up the object in Varnish.

  hash_data(req.url);

  if (req.http.host) {
    hash_data(req.http.host);
  } else {
    hash_data(server.ip);
  }
  # add the value of the osf cookie to the hash
  if (req.http.Cookie ~ "^.*osf.*?=.*$") {
    hash_data(regsuball(req.http.Cookie, "^.*osf.*?=(\S+?)[;|\s].*$", "\1"));
  }

  # Add the value of the authorization header to the hash
  # Accounts for oauth and PAT
  if (req.http.Authorization) {
  	hash_data(req.http.Authorization);
  }
}

sub vcl_backend_fetch {
	return (fetch);
}

sub vcl_miss {
	# Called after a cache lookup if the requested document was not found in the cache. Its purpose
	# is to decide whether or not to attempt to retrieve the document from the backend, and which
	# backend to use.

	return (fetch);
}

sub add_hit_headers {
	if (obj.hits > 0) {
		set resp.http.X-Cache = "HIT";
		set resp.http.X-Cache-Hits = obj.hits;
	} else {
		set resp.http.X-Cache = "MISS";
	}
}

sub fix_headers {
	unset resp.http.X-Varnish;
	unset resp.http.Via;
	unset resp.http.X-Powered-By;
}

sub vcl_hit {
	if (obj.ttl >= 0s) {
		return(deliver);
	}
	if (std.healthy(req.backend_hint)) {
		# we let the object be 30s stale when backend is healthy
		if (obj.ttl + 30s > 0s) {
			return(deliver);
		} else {
			return(fetch);
		}
	} else {
		#we let the object be 1h stale when backend is sick
		if (obj.ttl + obj.grace > 0s) {
			return(deliver);
		} else {
			return(fetch);
		}
	}
	set req.http.X-obj-ttl = obj.ttl; # add ttl header
	set req.http.X-healthy = std.healthy(req.backend_hint); # add backend status
}

sub vcl_backend_response {
    # Happens after we have read the response headers from the backend.
    #
    # Here you clean the response headers, removing silly Set-Cookie headers
    # and other mistakes your backend does.

    # help background lurker to remove matching objects
    set beresp.http.x-url = bereq.url;
    # add backend server name header
    set beresp.http.X-Backend = beresp.backend.name;
    # add ttl header
    set beresp.http.X-beresp-ttl = beresp.ttl;

   	if (bereq.url ~ "esi=true") {
		set beresp.do_esi = true;
	}

	# Enable cache for all static files
	# The same argument as the static caches from above: monitor your cache size, if you get data nuked out of it, consider giving up the static file cache.
	# Before you blindly enable this, have a read here: https://ma.ttias.be/stop-caching-static-files/
	# if (bereq.url ~ "^[^?]*\.(bmp|bz2|css|doc|eot|flv|gif|gz|ico|jpeg|jpg|js|less|mp[34]|pdf|png|rar|rtf|swf|tar|tgz|txt|wav|woff|xml|zip|webm)(\?.*)?$") {
	# 	unset beresp.http.set-cookie;
	# }

	# Large static files are delivered directly to the end-user without
	# waiting for Varnish to fully read the file first.
	# Varnish 4 fully supports Streaming, so use streaming here to avoid locking.
	if (bereq.url ~ "^[^?]*\.(mp[34]|rar|tar|tgz|gz|wav|zip|bz2|xz|7z|avi|mov|ogm|mpe?g|mk[av]|webm)(\?.*)?$") {
		unset beresp.http.set-cookie;
		set beresp.do_stream = true;  # Check memory usage it'll grow in fetch_chunksize blocks (128k by default) if the backend doesn't send a Content-Length header, so only enable it for big objects
		set beresp.do_gzip = false;   # Don't try to compress it for storage
	}
	# Set 2min cache if unset for static files
	if (beresp.ttl <= 0s || beresp.http.Set-Cookie || beresp.http.Vary == "*") {
		set beresp.ttl = 120s; # Important, you shouldn't rely on this, SET YOUR HEADERS in the backend
		set beresp.uncacheable = true;
		return (deliver);
	}

	# Allow stale content, in case the backend goes down.
	# make Varnish keep all objects for 6 hours beyond their TTL
	set beresp.grace = 6h;

	return (deliver);
}

sub vcl_backend_error {
	set beresp.http.Content-Type = "text/html; charset=utf-8";
	set beresp.http.X-Backend = beresp.backend.name;
	set beresp.http.X-beresp-ttl = beresp.ttl;
}

sub vcl_deliver {
	# Called before a cached object is delivered to the client.

	if (obj.hits > 0) { # Add debug header to see if it's a HIT/MISS and the number of hits, disable when not needed
		set resp.http.X-Cache = "HIT";
	} else {
		set resp.http.X-Cache = "MISS";
	}

	call add_hit_headers;

	# Please note that obj.hits behaviour changed in 4.0, now it counts per objecthead, not per object
	# and obj.hits may not be reset in some cases where bans are in use. See bug 1492 for details.
	# So take hits with a grain of salt
	set resp.http.X-Cache-Hits = obj.hits;

	# remove the header that is used internally for ban
	unset resp.http.x-url;

	# # Remove some headers: PHP version
	# unset resp.http.X-Powered-By;

	# # Remove some headers: Apache version & OS
	# unset resp.http.Server;
	# unset resp.http.X-Drupal-Cache;
	# unset resp.http.X-Varnish;
	# unset resp.http.Via;
	# unset resp.http.Link;
	# unset resp.http.X-Generator;

	return (deliver);
}
