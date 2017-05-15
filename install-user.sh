#!/bin/bash
# userspace install

# make a virtualenv and activate it 
mkdir -p ~/venv
python -m virtualenv ~/venv
source ~/venv/bin/activate
export PATH=$PATH:~/project/node_modules/.bin

# make a project dir
mkdir -p ~/project
cd ~/project

# fakecas
wget https://github.com/CenterForOpenScience/fakecas/releases/download/0.2.0/fakecas.linux
mv fakecas.linux fakecas
chmod +x fakecas

pip install -U pip
pip install \
    invoke==0.11.0 \
    uwsgi==2.0.10

# copy config
cp website/settings/local-dist.py website/settings/local.py
cp api/base/settings/local-dist.py api/base/settings/local.py

# add virtualenv and npm to shells
echo 'source ~/venv/bin/activate' >> ~/.bashrc 
echo 'export PATH=$PATH:~/project/node_modules/.bin' >> ~/.bashrc

# install python dependencies
invoke requirements --quick

# fix uritemplate
pip uninstall -y uritemplate.py
pip install uritemplate.py==0.3.0

