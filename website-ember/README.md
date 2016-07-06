# Website-ember

This directory houses code and 

By design, it is considered separate from other OSF static assets. It has its own dependency list and build process.

## Prerequisites

You will need the following things properly installed on your computer.

* [Git](http://git-scm.com/)
* [Node.js](http://nodejs.org/) (with NPM)
* [Bower](http://bower.io/)
* [Ember CLI](http://ember-cli.com/)
* [PhantomJS](http://phantomjs.org/)

## Installation

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
 `AUTHORIZER=cookie BACKEND=local ember build --output-path ../website/static/public/ember/ --environment=production --watch`
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

Specify what it takes to deploy your app.

## Further Reading / Useful Links

* [ember.js](http://emberjs.com/)
* [ember-cli](http://ember-cli.com/)
* Development Browser Extensions
  * [ember inspector for chrome](https://chrome.google.com/webstore/detail/ember-inspector/bmdblncegkenkacieihfhpjfppoconhi)
  * [ember inspector for firefox](https://addons.mozilla.org/en-US/firefox/addon/ember-inspector/)

