server:
	export OSF_TEST_DB=0 && python main.py

mongo:
	mongod --port 20771

requirements:
	pip install --upgrade -r requirements.txt

test:
	nosetests tests

# Testing views requires that a different DB is used
testserver:
	export OSF_TEST_DB="osf_test" && python main.py
