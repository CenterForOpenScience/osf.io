# OSF ShareLaTeX Addon

As ShareLaTeX public API is not yet merged on master and is not available on the service and website of same name,
you will need your own version of ShareLaTeX running with a patch applied to make it working.
The patch and pull request are available at:
https://github.com/sharelatex/web-sharelatex/pull/212

If you would like to see it merged to mainline ShareLaTeX, please leave a comment on the link above.

For instructions on ShareLaTeX installation, please, take a look at:
https://github.com/sharelatex/sharelatex/wiki/Setting-up-a-Development-Environment

Please note that you may already be running a MongoDB/TokuMX for OSF, the easiest way I solved this was to run another instance of it on another port and alter the sharelatex config to point to the correct one.
