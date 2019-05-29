FROM python:2.7-slim-stretch

ENV GOSU_VERSION=1.10 \
    NODE_ENV=production \
    NODE_VERSION=8.6.0 \
    YARN_VERSION=1.1.0

# Libraries such as matplotlib require a HOME directory for cache and configuration
RUN set -ex \
    && mkdir -p /var/www \
    && chown www-data:www-data /var/www \
    && apt-get update \
    && apt-get install -y gnupg2 \
    && for key in \
      # GOSU
      B42F6819007F00F88E364FD4036A9C25BF357DD4 \
      # https://github.com/nodejs/docker-node/blob/9c25cbe93f9108fd1e506d14228afe4a3d04108f/8.2/Dockerfile
      # gpg keys listed at https://github.com/nodejs/node#release-team
      # Node
      9554F04D7259F04124DE6B476D5A82AC7E37093B \
      94AE36675C464D64BAFA68DD7434390BDBE9B9C5 \
      FD3A5288F042B6850C66B31F09FE44734EB7990E \
      71DCFD284A79C3B38668286BC97EC7A07EDE3FC1 \
      DD8F2338BAE7501E3DD5AC78C273792F7D83545D \
      B9AE9905FFD7803F25714661B63B535A4C206CA9 \
      C4F0DFFF4E8C1A8236409D08E73BC641CC11F4C8 \
      56730D5401028683275BD23C23EFEFE93C4CFFFE \
      # Yarn
      6A010C5166006599AA17F08146C2130DFD2497F5 \
    ; do \
      gpg --keyserver hkp://ipv4.pool.sks-keyservers.net:80 --recv-keys "$key" || \
      gpg --keyserver hkp://ha.pool.sks-keyservers.net:80 --recv-keys "$key" || \
      gpg --keyserver hkp://pgp.mit.edu:80 --recv-keys "$key" || \
      gpg --keyserver hkp://keyserver.pgp.com:80 --recv-keys "$key" \
    ; done \
    # Install dependancies
    && apt-get install -y \
        git \
        libev4 \
        libev-dev \
        libevent-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        curl \
        # cryptography
        build-essential \
        libssl-dev \
        libffi-dev \
        python-dev \
        # postgresql
        libpq-dev \
        # file audits
        par2 \
    && ARCH= \
    && dpkgArch="$(dpkg --print-architecture)" \
    && case "${dpkgArch##*-}" in \
      amd64) ARCH='x64';; \
      ppc64el) ARCH='ppc64le';; \
      *) echo "unsupported architecture"; exit 1 ;; \
    esac \
    # grab gosu for easy step-down from root
    && curl -o /usr/local/bin/gosu -SL "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch" \
    && curl -o /usr/local/bin/gosu.asc -SL "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch.asc" \
    && gpg --verify /usr/local/bin/gosu.asc \
    && rm /usr/local/bin/gosu.asc \
    && chmod +x /usr/local/bin/gosu \
    # Node
    && curl -SLO "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-$ARCH.tar.xz" \
    && curl -SLO --compressed "https://nodejs.org/dist/v$NODE_VERSION/SHASUMS256.txt.asc" \
    && gpg --batch --decrypt --output SHASUMS256.txt SHASUMS256.txt.asc \
    && grep " node-v$NODE_VERSION-linux-$ARCH.tar.xz\$" SHASUMS256.txt | sha256sum -c - \
    && tar -xJf "node-v$NODE_VERSION-linux-$ARCH.tar.xz" -C /usr/local --strip-components=1 \
    && rm "node-v$NODE_VERSION-linux-$ARCH.tar.xz" SHASUMS256.txt.asc SHASUMS256.txt \
    && ln -s /usr/local/bin/node /usr/local/bin/nodejs \
    # Yarn
    && curl -fSLO --compressed "https://yarnpkg.com/downloads/$YARN_VERSION/yarn-v$YARN_VERSION.tar.gz" \
    && curl -fSLO --compressed "https://yarnpkg.com/downloads/$YARN_VERSION/yarn-v$YARN_VERSION.tar.gz.asc" \
    && gpg --batch --verify yarn-v$YARN_VERSION.tar.gz.asc yarn-v$YARN_VERSION.tar.gz \
    && mkdir -p /opt/yarn \
    && tar -xzf yarn-v$YARN_VERSION.tar.gz -C /opt/yarn --strip-components=1 \
    && ln -s /opt/yarn/bin/yarn /usr/local/bin/yarn \
    && ln -s /opt/yarn/bin/yarn /usr/local/bin/yarnpkg \
    && yarn global add bower \
    && yarn cache clean \
    && rm -rf \
        yarn-v$YARN_VERSION.tar.gz.asc \
        yarn-v$YARN_VERSION.tar.gz \
        $HOME/.gnupg \
        $HOME/.cache \
    && apt-get remove -y \
        curl \
    && apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /code

WORKDIR /code

COPY ./requirements.txt ./
COPY ./requirements/ ./requirements/
COPY ./addons/bitbucket/requirements.txt ./addons/bitbucket/
COPY ./addons/box/requirements.txt ./addons/box/
#COPY ./addons/citations/requirements.txt ./addons/citations/
COPY ./addons/dataverse/requirements.txt ./addons/dataverse/
COPY ./addons/dropbox/requirements.txt ./addons/dropbox/
#COPY ./addons/figshare/requirements.txt ./addons/figshare/
#COPY ./addons/forward/requirements.txt ./addons/forward/
COPY ./addons/github/requirements.txt ./addons/github/
COPY ./addons/gitlab/requirements.txt ./addons/gitlab/
#COPY ./addons/googledrive/requirements.txt ./addons/googledrive/
COPY ./addons/mendeley/requirements.txt ./addons/mendeley/
COPY ./addons/onedrive/requirements.txt /code/addons/onedrive/
#COPY ./addons/osfstorage/requirements.txt ./addons/osfstorage/
COPY ./addons/owncloud/requirements.txt ./addons/owncloud/
COPY ./addons/s3/requirements.txt ./addons/s3/
COPY ./addons/twofactor/requirements.txt ./addons/twofactor/
#COPY ./addons/wiki/requirements.txt ./addons/wiki/
COPY ./addons/zotero/requirements.txt ./addons/zotero/

RUN for reqs_file in \
        /code/requirements.txt \
        /code/requirements/release.txt \
        /code/addons/*/requirements.txt \
    ; do \
        pip install --no-cache-dir -c /code/requirements/constraints.txt -r "$reqs_file" \
    ; done \
    && (pip uninstall uritemplate.py --yes || true) \
    && pip install --no-cache-dir uritemplate.py==0.3.0 \
    # Fix: https://github.com/CenterForOpenScience/osf.io/pull/6783
    && python -m compileall /usr/local/lib/python2.7 || true

# OSF: Assets
COPY ./.bowerrc ./bower.json ./
RUN bower install --production --allow-root \
    && bower cache clean --allow-root

COPY ./package.json ./.yarnrc ./yarn.lock ./
RUN yarn install --frozen-lockfile \
    && yarn cache clean

COPY ./tasks/ ./tasks/
COPY ./website/settings/ ./website/settings/
COPY ./api/base/settings/ ./api/base/settings/
COPY ./website/__init__.py ./website/__init__.py
COPY ./addons.json ./addons.json
RUN mv ./website/settings/local-dist.py ./website/settings/local.py \
    && mv ./api/base/settings/local-dist.py ./api/base/settings/local.py \
    && sed 's/DEBUG_MODE = True/DEBUG_MODE = False/' -i ./website/settings/local.py

COPY ./webpack* ./
COPY ./website/static/ ./website/static/
COPY ./addons/bitbucket/static/ ./addons/bitbucket/static/
COPY ./addons/box/static/ ./addons/box/static/
COPY ./addons/citations/static/ ./addons/citations/static/
COPY ./addons/dataverse/static/ ./addons/dataverse/static/
COPY ./addons/dropbox/static/ ./addons/dropbox/static/
COPY ./addons/figshare/static/ ./addons/figshare/static/
COPY ./addons/forward/static/ ./addons/forward/static/
COPY ./addons/github/static/ ./addons/github/static/
COPY ./addons/gitlab/static/ ./addons/gitlab/static/
COPY ./addons/googledrive/static/ ./addons/googledrive/static/
COPY ./addons/mendeley/static/ ./addons/mendeley/static/
COPY ./addons/onedrive/static/ /code/addons/onedrive/static/
COPY ./addons/osfstorage/static/ ./addons/osfstorage/static/
COPY ./addons/owncloud/static/ ./addons/owncloud/static/
COPY ./addons/s3/static/ ./addons/s3/static/
COPY ./addons/twofactor/static/ ./addons/twofactor/static/
COPY ./addons/wiki/static/ ./addons/wiki/static/
COPY ./addons/zotero/static/ ./addons/zotero/static/
RUN mkdir -p ./website/static/built/ \
    && invoke build_js_config_files \
    && yarn run webpack-prod
# /OSF: Assets

# Admin: Assets
COPY ./admin/.bowerrc ./admin/bower.json ./admin/
RUN cd ./admin \
    && bower install --production --allow-root \
    && bower cache clean --allow-root

COPY ./admin/package.json ./admin/yarn.lock ./admin/
RUN cd ./admin \
    && yarn install --frozen-lockfile \
    && yarn cache clean

COPY ./admin/webpack* ./admin/
COPY ./admin/static/ ./admin/static/
RUN cd ./admin \
    && yarn run webpack-prod
# /Admin: Assets

# Copy the rest of the code over
COPY ./ ./

ARG GIT_COMMIT=
ENV GIT_COMMIT ${GIT_COMMIT}

RUN for module in \
        api.base.settings \
        admin.base.settings \
    ; do \
        export DJANGO_SETTINGS_MODULE=$module \
        && python manage.py collectstatic --noinput --no-init-app \
    ; done \
    && for file in \
        ./website/templates/_log_templates.mako \
        ./website/static/built/nodeCategories.json \
    ; do \
        touch $file && chmod o+w $file \
    ; done \
    && rm ./website/settings/local.py ./api/base/settings/local.py

CMD ["gosu", "nobody", "invoke", "--list"]
