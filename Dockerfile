FROM python:2.7-slim

# Libraries such as matplotlib require a HOME directory for cache and configuration
RUN usermod -d /home www-data && chown www-data:www-data /home

# Install dependancies
RUN apt-get update \
    && apt-get install -y \
        git \
        libev4 \
        libev-dev \
        libevent-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        curl \
        # matplotlib
        libfreetype6-dev \
        libxft-dev \
        # scipy
        gfortran \
        libopenblas-dev \
        liblapack-dev \
        # cryptography
        build-essential \
        libssl-dev \
        libffi-dev \
        python-dev \
        # postgresql
        libpq-dev \
    && apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# grab gosu for easy step-down from root
ENV GOSU_VERSION 1.4
RUN apt-get update \
    && gpg --keyserver pool.sks-keyservers.net --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 \
    && curl -o /usr/local/bin/gosu -SL "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$(dpkg --print-architecture)" \
    && curl -o /usr/local/bin/gosu.asc -SL "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$(dpkg --print-architecture).asc" \
    && gpg --verify /usr/local/bin/gosu.asc \
    && rm /usr/local/bin/gosu.asc \
    && chmod +x /usr/local/bin/gosu \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# https://github.com/nodejs/docker-node/blob/9c25cbe93f9108fd1e506d14228afe4a3d04108f/8.2/Dockerfile
# gpg keys listed at https://github.com/nodejs/node#release-team
RUN set -ex \
  && for key in \
    9554F04D7259F04124DE6B476D5A82AC7E37093B \
    94AE36675C464D64BAFA68DD7434390BDBE9B9C5 \
    FD3A5288F042B6850C66B31F09FE44734EB7990E \
    71DCFD284A79C3B38668286BC97EC7A07EDE3FC1 \
    DD8F2338BAE7501E3DD5AC78C273792F7D83545D \
    B9AE9905FFD7803F25714661B63B535A4C206CA9 \
    C4F0DFFF4E8C1A8236409D08E73BC641CC11F4C8 \
    56730D5401028683275BD23C23EFEFE93C4CFFFE \
  ; do \
    gpg --keyserver pgp.mit.edu --recv-keys "$key" || \
    gpg --keyserver keyserver.pgp.com --recv-keys "$key" || \
    gpg --keyserver ha.pool.sks-keyservers.net --recv-keys "$key" ; \
  done

ENV NPM_CONFIG_LOGLEVEL info
ENV NODE_VERSION 8.2.1

RUN ARCH= && dpkgArch="$(dpkg --print-architecture)" \
  && case "${dpkgArch##*-}" in \
    amd64) ARCH='x64';; \
    ppc64el) ARCH='ppc64le';; \
    *) echo "unsupported architecture"; exit 1 ;; \
  esac \
  && curl -SLO "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-$ARCH.tar.xz" \
  && curl -SLO --compressed "https://nodejs.org/dist/v$NODE_VERSION/SHASUMS256.txt.asc" \
  && gpg --batch --decrypt --output SHASUMS256.txt SHASUMS256.txt.asc \
  && grep " node-v$NODE_VERSION-linux-$ARCH.tar.xz\$" SHASUMS256.txt | sha256sum -c - \
  && tar -xJf "node-v$NODE_VERSION-linux-$ARCH.tar.xz" -C /usr/local --strip-components=1 \
  && rm "node-v$NODE_VERSION-linux-$ARCH.tar.xz" SHASUMS256.txt.asc SHASUMS256.txt \
  && ln -s /usr/local/bin/node /usr/local/bin/nodejs

ENV YARN_VERSION 0.27.5

RUN set -ex \
  && for key in \
    6A010C5166006599AA17F08146C2130DFD2497F5 \
  ; do \
    gpg --keyserver pgp.mit.edu --recv-keys "$key" || \
    gpg --keyserver keyserver.pgp.com --recv-keys "$key" || \
    gpg --keyserver ha.pool.sks-keyservers.net --recv-keys "$key" ; \
  done \
  && curl -fSLO --compressed "https://yarnpkg.com/downloads/$YARN_VERSION/yarn-v$YARN_VERSION.tar.gz" \
  && curl -fSLO --compressed "https://yarnpkg.com/downloads/$YARN_VERSION/yarn-v$YARN_VERSION.tar.gz.asc" \
  && gpg --batch --verify yarn-v$YARN_VERSION.tar.gz.asc yarn-v$YARN_VERSION.tar.gz \
  && mkdir -p /opt/yarn \
  && tar -xzf yarn-v$YARN_VERSION.tar.gz -C /opt/yarn --strip-components=1 \
  && ln -s /opt/yarn/bin/yarn /usr/local/bin/yarn \
  && ln -s /opt/yarn/bin/yarn /usr/local/bin/yarnpkg \
  && rm yarn-v$YARN_VERSION.tar.gz.asc yarn-v$YARN_VERSION.tar.gz

RUN mkdir -p /code
WORKDIR /code

RUN pip install -U pip

COPY ./requirements.txt /code/
COPY ./requirements/ /code/requirements/

COPY ./addons/bitbucket/requirements.txt /code/addons/bitbucket/
COPY ./addons/box/requirements.txt /code/addons/box/
COPY ./addons/dataverse/requirements.txt /code/addons/dataverse/
COPY ./addons/dropbox/requirements.txt /code/addons/dropbox/
COPY ./addons/github/requirements.txt /code/addons/github/
COPY ./addons/mendeley/requirements.txt /code/addons/mendeley/
COPY ./addons/owncloud/requirements.txt /code/addons/owncloud/
COPY ./addons/s3/requirements.txt /code/addons/s3/
COPY ./addons/twofactor/requirements.txt /code/addons/twofactor/
COPY ./addons/zotero/requirements.txt /code/addons/zotero/

RUN pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/requirements.txt \
    && pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/requirements/release.txt

RUN pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/addons/box/requirements.txt \
    && pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/addons/bitbucket/requirements.txt \
    && pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/addons/dataverse/requirements.txt \
    && pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/addons/dropbox/requirements.txt \
    && pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/addons/github/requirements.txt \
    && pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/addons/mendeley/requirements.txt \
    && pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/addons/owncloud/requirements.txt \
    && pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/addons/s3/requirements.txt \
    && pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/addons/twofactor/requirements.txt \
    && pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/addons/zotero/requirements.txt

RUN (pip uninstall uritemplate.py --yes || true) \
    && pip install --no-cache-dir uritemplate.py==0.3.0

# Fix: https://github.com/CenterForOpenScience/osf.io/pull/6783
RUN python -m compileall /usr/local/lib/python2.7 || true

# OSF: Assets
COPY ./.bowerrc /code/
COPY ./bower.json /code/
RUN npm install bower \
    && ./node_modules/bower/bin/bower install --allow-root \
    && ./node_modules/bower/bin/bower cache clean --allow-root

COPY ./package.json ./.npmrc /code/
RUN npm install --production

COPY ./tasks /code/tasks
COPY ./website/settings /code/website/settings/
COPY ./api/base/settings /code/api/base/settings/
COPY ./website/__init__.py /code/website/__init__.py
COPY ./addons.json /code/addons.json
RUN mv /code/website/settings/local-dist.py /code/website/settings/local.py \
    && mv /code/api/base/settings/local-dist.py /code/api/base/settings/local.py \
    && sed 's/DEBUG_MODE = True/DEBUG_MODE = False/' -i /code/website/settings/local.py

COPY ./webpack* /code/
COPY ./website/static /code/website/static/
COPY ./addons/bitbucket/static/ /code/addons/bitbucket/static/
COPY ./addons/box/static/ /code/addons/box/static/
COPY ./addons/citations/static/ /code/addons/citations/static/
COPY ./addons/dataverse/static/ /code/addons/dataverse/static/
COPY ./addons/dropbox/static/ /code/addons/dropbox/static/
COPY ./addons/figshare/static/ /code/addons/figshare/static/
COPY ./addons/forward/static/ /code/addons/forward/static/
COPY ./addons/github/static/ /code/addons/github/static/
COPY ./addons/googledrive/static/ /code/addons/googledrive/static/
COPY ./addons/mendeley/static/ /code/addons/mendeley/static/
COPY ./addons/osfstorage/static/ /code/addons/osfstorage/static/
COPY ./addons/owncloud/static/ /code/addons/owncloud/static/
COPY ./addons/s3/static/ /code/addons/s3/static/
COPY ./addons/twofactor/static/ /code/addons/twofactor/static/
COPY ./addons/wiki/static/ /code/addons/wiki/static/
COPY ./addons/zotero/static/ /code/addons/zotero/static/
RUN mkdir -p /code/website/static/built/ \
    && invoke build_js_config_files \
    && node ./node_modules/webpack/bin/webpack.js --config webpack.prod.config.js \
    # && rm -rf /code/node_modules \ (needed for sharejs)
    && npm install @centerforopenscience/list-of-licenses \
    && rm -rf /root/.npm \
    && npm cache clean --force
# /OSF: Assets

# Admin: Assets
WORKDIR /code/admin

COPY ./admin/.bowerrc /code/admin/
COPY ./admin/bower.json /code/admin/
RUN mkdir node_modules \
    && npm install bower \
    && ./node_modules/bower/bin/bower install --allow-root \
    && ./node_modules/bower/bin/bower cache clean --allow-root

COPY ./admin/package.json /code/admin/
RUN npm install --production

COPY ./admin/webpack* /code/admin/
COPY ./admin/static /code/admin/static/

RUN node ./node_modules/webpack/bin/webpack.js --config webpack.prod.config.js \
    && rm -rf /root/.npm \
    && npm cache clean --force

WORKDIR /code
# /Admin: Assets


# Copy the rest of the code over
COPY ./ /code/

ARG GIT_COMMIT=
ENV GIT_COMMIT ${GIT_COMMIT}

RUN export DJANGO_SETTINGS_MODULE=api.base.settings && python manage.py collectstatic --noinput --no-init-app \
    && export DJANGO_SETTINGS_MODULE=admin.base.settings && python manage.py collectstatic --noinput --no-init-app

RUN touch /code/website/templates/_log_templates.mako \
    && chmod o+w /code/website/templates/_log_templates.mako \
    && touch /code/website/static/built/nodeCategories.json \
    && chmod o+w /code/website/static/built/nodeCategories.json \
    && rm /code/website/settings/local.py /code/api/base/settings/local.py

CMD ["gosu", "nobody", "invoke", "--list"]
