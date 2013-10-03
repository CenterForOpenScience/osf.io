server:
	unset OSF_TEST_DB && python main.py

mongo:
	mongod --port 20771

requirements:
	pip install --upgrade -r requirements.txt

test:
	nosetests tests

# Testing views requires that a different DB is used
testserver:
	export OSF_TEST_DB="osf_test" && python main.py
