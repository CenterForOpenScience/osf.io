# Website-ember

This directory houses code and assets used in the OSF Ember SPA, a future planned rewrite.

By design, it is considered separate from other OSF static assets. It has its own dependency list and build process.

## Prerequisites

You will need the following things properly installed on your computer.

* [Git](http://git-scm.com/)
* [Node.js](http://nodejs.org/) (with NPM)
* [Bower](http://bower.io/)
* [Ember CLI](http://ember-cli.com/)
* [PhantomJS](http://phantomjs.org/)

## Installation

This application may be hidden behind a feature flag. Set `USE_EMBER=True` in your `local.py` file to make the routes
 accessible for local development.

* `git clone <repository-url>` this repository
* change into the `website-ember` directory
* Follow the [steps](https://github.com/CenterForOpenScience/ember-osf#using-this-code-in-an-ember-app) to install
 and configure the ember-osf addon with this application. (`ember install ../../ember-osf && npm link ../../ember-osf && ember generate ember-osf`)
* `npm install`
* `bower install`

## Running / Development
For local development, this is designed to run alongside (and from within) the flask application.

1. Define the same route in the flask application (`routes.py`) and the ember application (`router.js`). 
2. Build the assets from a location that the flask application can serve, using the following command:
 `ember build --output-path ../website/static/public/ember/ --watch`
3. Visit your app at http://localhost:5000/<routename>

### Code Generators

Make use of the many generators for code, try `ember help generate` for more details

### Running Tests

* `ember test`
* `ember test --server`

### Building

* `ember build` (development)
* `ember build --environment production` (production)

### Deploying

Will likely require nginx config changes to dispatch known routes to serve the ember app.
