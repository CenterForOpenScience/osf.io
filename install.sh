# Install dependancies
apt-get update \
    && apt-get install -y \
        python2.7-dev \
        git \
        libev4 \
        libev-dev \
        libevent-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        build-essential \
        libssl-dev \
        libffi-dev \
        python-dev \
    && apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Node : https://registry.hub.docker.com/u/library/node/
export NODE_VERSION=0.12.4
export NPM_VERSION=2.10.1
apt-get update \
    && apt-get install -y \
        curl \
    && gpg --keyserver pool.sks-keyservers.net --recv-keys 7937DFD2AB06298B2293C3187D33FF9D0246406D 114F43EE0176B71C7BC219DD50A3051F888C628D \
    && curl -SLO "http://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.gz" \
  	&& curl -SLO "http://nodejs.org/dist/v$NODE_VERSION/SHASUMS256.txt.asc" \
  	&& gpg --verify SHASUMS256.txt.asc \
  	&& grep " node-v$NODE_VERSION-linux-x64.tar.gz\$" SHASUMS256.txt.asc | sha256sum -c - \
  	&& tar -xzf "node-v$NODE_VERSION-linux-x64.tar.gz" -C /usr/local --strip-components=1 \
  	&& rm "node-v$NODE_VERSION-linux-x64.tar.gz" SHASUMS256.txt.asc \
  	&& npm install -g npm@"$NPM_VERSION" \
  	&& npm cache clear \
    && apt-get clean \
    && apt-get autoremove -y \
        curl \
    && rm -rf /var/lib/apt/lists/*

# tokumx
apt-key adv --keyserver keyserver.ubuntu.com --recv-key 505A7412
echo "deb [arch=amd64] http://s3.amazonaws.com/tokumx-debs $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/tokumx.list
apt-get update
apt-get install tokumx

# fakecas
curl https://github.com/CenterForOpenScience/fakecas/releases/download/0.2.0/fakecas.linux
mv fakecas.linux fakecas
chmod +x fakecas


pip install -U pip

npm install -g bower \
    && pip install \
        invoke==0.11.0 \
        uwsgi==2.0.10

# copy config
cp website/settings/local-dist.py cp website/settings/local.py
cp api/base/settings/local-dist.py api/base/settings/local.py

# install things
invoke requirements --base --addons --dev
invoke setup

# tokumx
apt-key adv --keyserver keyserver.ubuntu.com --recv-key 505A7412
echo "deb [arch=amd64] http://s3.amazonaws.com/tokumx-debs $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/tokumx.list
apt-get update
apt-get install tokumx

