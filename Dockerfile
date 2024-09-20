FROM python:3.12-alpine3.17 AS base

# Creation of www-data group was removed as it is created by default in alpine 3.14 and higher
# Alpine does not create a www-data user, so we still need to create that. 82 is the standard
# uid/guid for www-data in Alpine.
RUN set -x \
    && adduser -h /var/www -u 82 -D -S -G www-data www-data

RUN apk add --no-cache --virtual .run-deps \
    gcc \
    g++ \
    nodejs \
    npm \
    yarn \
    libxslt-dev \
    su-exec \
    bash \
    git \
    libxml2 \
    libxslt \
    libpq-dev \
    libffi \
    libev \
    libevent \
    && yarn global add bower \
    && mkdir -p /var/www \
    && chown www-data:www-data /var/www

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_OPTIONS_ALWAYS_COPY=1 \
    POETRY_VIRTUALENVS_CREATE=0

FROM base AS build

ENV POETRY_VIRTUALENVS_IN_PROJECT=1 \
    YARN_CACHE_FOLDER=/tmp/yarn-cache \
    POETRY_CACHE_DIR=/tmp/poetry-cache \
    POETRY_HOME=/tmp/poetry

RUN python3 -m venv $POETRY_HOME
RUN $POETRY_HOME/bin/pip install poetry==1.8.3


RUN set -ex \
    && apk add --no-cache --virtual .build-deps \
        build-base \
        linux-headers \
        musl-dev \
        libxml2-dev \
        libxslt-dev \
        # cryptography
        libffi-dev

WORKDIR /code
COPY pyproject.toml .
COPY poetry.lock .
# Fix: https://github.com/CenterForOpenScience/osf.io/pull/6783
RUN $POETRY_HOME/bin/poetry install --without=dev --no-root --compile

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
COPY ./addons/boa/static/ ./addons/boa/static/
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
    && python3 -m invoke build-js-config-files \
    && yarn run webpack-prod \
    # Admin
    && cd ./admin \
    && yarn install --frozen-lockfile \
    && yarn run webpack-prod \
    && cd ../ \
    # Cleanup
    && yarn cache clean \
    && npm cache clean --force

# Copy the rest of the code over
COPY ./ ./

ARG GIT_COMMIT=
ENV GIT_COMMIT=${GIT_COMMIT}

# TODO: Admin/API should fully specify their bower static deps, and not
#       include ./website/static in their defaults.py.
#       (this adds an additional 300+mb to the build image)

RUN for module in \
       api.base.settings \
       admin.base.settings \
   ; do \
       export DJANGO_SETTINGS_MODULE=$module \
       && python3 manage.py collectstatic --noinput --no-init-app \
   ; done \
   && for file in \
       ./website/templates/_log_templates.mako \
       ./website/static/built/nodeCategories.json \
   ; do \
       touch $file && chmod o+w $file \
   ; done \
   && rm ./website/settings/local.py ./api/base/settings/local.py

FROM base AS runtime

WORKDIR /code
COPY --from=build /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /code /code

CMD ["su-exec", "nobody", "python", "-m", "invoke", "--list"]
