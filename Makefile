server:
	python main.py

mongo:
	mongod --port 20771

mongoshell:
	mongo osf20130903 --port 20771

requirements:
	pip install --upgrade -r dev-requirements.txt

test:
	nosetests tests/
