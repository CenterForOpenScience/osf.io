FROM node:8-alpine

# Source: https://github.com/docker-library/httpd/blob/7976cabe162268bd5ad2d233d61e340447bfc371/2.4/alpine/Dockerfile#L3
RUN set -x \
    && addgroup -g 82 -S www-data \
    && adduser -u 82 -D -S -G www-data www-data

RUN apk add --no-cache --virtual .run-deps \
    su-exec \
    bash \
    python \
    py-pip \
    git \
    # lxml2
    libxml2 \
    libxslt \
    # psycopg2
    postgresql-libs \
    # cryptography
    libffi \
    # gevent
    libev \
    libevent \
    && yarn global add bower

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

RUN set -ex \
    && mkdir -p /var/www \
    && chown www-data:www-data /var/www \
    && apk add --no-cache --virtual .build-deps \
        build-base \
        linux-headers \
        python-dev \
        # lxml2
        musl-dev \
        libxml2-dev \
        libxslt-dev \
        # psycopg2
        postgresql-dev \
        # cryptography
        libffi-dev \
    && for reqs_file in \
        /code/requirements.txt \
        /code/requirements/release.txt \
        /code/addons/*/requirements.txt \
    ; do \
        pip install --no-cache-dir -c /code/requirements/constraints.txt -r "$reqs_file" \
    ; done \
    && (pip uninstall uritemplate.py --yes || true) \
    && pip install --no-cache-dir uritemplate.py==0.3.0 \
    # Fix: https://github.com/CenterForOpenScience/osf.io/pull/6783
    && python -m compileall /usr/lib/python2.7 || true \
    && apk del .build-deps

# Settings
COPY ./tasks/ ./tasks/
COPY ./website/settings/ ./website/settings/
COPY ./api/base/settings/ ./api/base/settings/
COPY ./website/__init__.py ./website/__init__.py
COPY ./addons.json ./addons.json
RUN mv ./website/settings/local-dist.py ./website/settings/local.py \
    && mv ./api/base/settings/local-dist.py ./api/base/settings/local.py \
    && sed 's/DEBUG_MODE = True/DEBUG_MODE = False/' -i ./website/settings/local.py

# Bower Assets
COPY ./.bowerrc ./bower.json ./
COPY ./admin/.bowerrc ./admin/bower.json ./admin/
RUN \
    # OSF
    bower install --production --allow-root \
    && bower cache clean --allow-root \
    # Admin
    && cd ./admin \
    && bower install --production --allow-root \
    && bower cache clean --allow-root

# Webpack Assets
#
## OSF
COPY ./package.json ./.yarnrc ./yarn.lock ./
COPY ./webpack* ./
COPY ./website/static/ ./website/static/
## Admin
COPY ./admin/package.json ./admin/yarn.lock ./admin/
COPY ./admin/webpack* ./admin/
COPY ./admin/static/ ./admin/static/
## Addons
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
RUN \
    # OSF
    yarn install --frozen-lockfile \
    && mkdir -p ./website/static/built/ \
    && invoke build_js_config_files \
    && yarn run webpack-prod \
    # Admin
    && cd ./admin \
    && yarn install --frozen-lockfile \
    && yarn run webpack-prod \
    && cd ../ \
    # Cleanup
    && yarn cache clean \
    && rm -Rf node_modules \
    && rm -Rf ./admin/node_modules

# Copy the rest of the code over
COPY ./ ./

ARG GIT_COMMIT=
ENV GIT_COMMIT ${GIT_COMMIT}

# TODO: Admin/API should fully specify their bower static deps, and not include ./website/static in their defaults.py.
#       (this adds an additional 300+mb to the build image)
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

CMD ["su-exec", "nobody", "invoke", "--list"]
