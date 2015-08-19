OSF Style Guidelines
=========

This project aims to bring together resources to build Design and Layout of OSF components. As you are working with OSF please use this project as reference for how elements on your page should look and how the HTML and CSS should be used. This is a collaborative project so feel free to suggest changes or Pull Requests.
### Quick Start
* Clone the remote repo to your local

        $ git clone https://github.com/caneruguz/osf-style.git
        $ cd osf-style
    
* Install the dependent libraries (listed in [package.json](https://github.com/haoyuchen1992/osf-style/blob/Edit-Readme/package.json)) with npm

        $ npm install

* Besides those dependencies, SASS should also be installed to compile the SASS code in this repo. 

        $ sudo gem install sass
[Click here](http://sass-lang.com/install) for more details about installation of SASS.     
    
* Then run gulp script and the project dashboard could be found in `http://localhost:8000/`

        $ npm run gulp
After that, click `index.html` in the list directory and now the guideline page will show in your browser.

With the help of gulp, every change in repo code will automatically be complied and changed after saving.  

### Libraries Used Here
This Project relies on these technologies for its workflow so it's important to familiarize yourself before starting.

1. [Npm](https://www.npmjs.org) 
Node package management, for server side dependencies and making gulp work. We will use it to install all the dependent libraries(such as Gulp) in package.json.

2. [Gulp](http://gulpjs.com/)  
Builds the distribution by running important tasks including concatenation, minification(we are not doing this yet, but will), compiling less files.

3. [Bootstrap](http://getbootstrap.com/)  
Forms the basic design with flat colors taken from elsewhere. If you are working with html you need to use the Bootstrap syntax. 
