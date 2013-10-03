server:
	python main.py

mongo:
	mongod --port 20771

requirements:
	pip install --upgrade -r requirements.txt

test:
	nosetests tests
