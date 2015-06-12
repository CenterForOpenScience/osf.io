// for public activity page under explore nav-tag
require('../../css/pages/home-page.css');


var SignUp = require('../signUp.js');

new SignUp('#signUpScope', '/api/v1/register/');
