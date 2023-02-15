FROM python:3.11.1-alpine


RUN set -eux \
    & apk add \
        --no-cache \
        nodejs \
        yarn

RUN apk add --no-cache --virtual .run-deps \
    gcc \
    g++ \
    python3-dev \
    libxslt-dev \
    su-exec \
    bash \
    python3 \
    git \
    libxml2 \
    libxslt \
    postgresql-libs \
    libffi \
    libev \
    libevent \
    && yarn global add bower

WORKDIR /code

COPY ./requirements.txt ./
COPY ./requirements/ ./requirements/
COPY ./addons/bitbucket/requirements.txt ./addons/bitbucket/
COPY ./addons/box/requirements.txt ./addons/box/
COPY ./addons/dataverse/requirements.txt ./addons/dataverse/
COPY ./addons/dropbox/requirements.txt ./addons/dropbox/
COPY ./addons/github/requirements.txt ./addons/github/
COPY ./addons/gitlab/requirements.txt ./addons/gitlab/
COPY ./addons/mendeley/requirements.txt ./addons/mendeley/
COPY ./addons/onedrive/requirements.txt /code/addons/onedrive/
COPY ./addons/owncloud/requirements.txt ./addons/owncloud/
COPY ./addons/s3/requirements.txt ./addons/s3/
COPY ./addons/twofactor/requirements.txt ./addons/twofactor/
COPY ./addons/zotero/requirements.txt ./addons/zotero/

RUN set -ex \
    && mkdir -p /var/www \
    && apk add --no-cache --virtual .build-deps \
        build-base \
        linux-headers \
        python3-dev \
        musl-dev \
        libxml2-dev \
        libxslt-dev \
        postgresql-dev \
        libffi-dev


RUN  pip3 install --no-cache-dir -r /code/requirements.txt
RUN  pip3 install --no-cache-dir -r /code/requirements/release.txt
RUN  pip3 install --no-cache-dir -r /code/addons/bitbucket/requirements.txt
RUN  pip3 install --no-cache-dir -r /code/addons/box/requirements.txt
# RUN  pip3 install --no-cache-dir -r /code/addons/citations/requirements.txt
RUN  pip3 install --no-cache-dir -r /code/addons/dataverse/requirements.txt
RUN  pip3 install --no-cache-dir -r /code/addons/dropbox/requirements.txt
# RUN  pip3 install --no-cache-dir -r /code/addons/figshare/requirements.txt
# RUN  pip3 install --no-cache-dir -r /code/addons/forward/requirements.txt
RUN  pip3 install --no-cache-dir -r /code/addons/github/requirements.txt
RUN  pip3 install --no-cache-dir -r /code/addons/gitlab/requirements.txt
# RUN  pip3 install --no-cache-dir -r /code/addons/googledrive/requirements.txt
RUN  pip3 install --no-cache-dir -r /code/addons/mendeley/requirements.txt
RUN  pip3 install --no-cache-dir -r /code/addons/onedrive/requirements.txt
# RUN  pip3 install --no-cache-dir -r /code/addons/osfstorage/requirements.txt
RUN  pip3 install --no-cache-dir -r /code/addons/owncloud/requirements.txt
RUN  pip3 install --no-cache-dir -r /code/addons/s3/requirements.txt
# RUN  pip3 install --no-cache-dir -r /code/addons/wiki/requirements.txt
# RUN  pip3 install --no-cache-dir -r /code/addons/zotero/requirements.txt

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

RUN pip3 install --upgrade setuptools
RUN pip3 install invoke==2.0.0

RUN \
    # OSF
    yarn install --frozen-lockfile \
    && mkdir -p ./website/static/built/ \
    && invoke build-js-config-files \
    && yarn run webpack-prod \
    # Admin
    && cd ./admin \
    && yarn install --frozen-lockfile \
    && yarn run webpack-prod \
    && cd ../ \
    # Cleanup
    && yarn cache clean \

# RUN export DJANGO_SETTINGS_MODULE=api.base.settings
# RUN python3 ~/manage.py collectstatic --noinput --no-init-app
# RUN export DJANGO_SETTINGS_MODULE=admin.base.settings
# RUN python3 ~/manage.py collectstatic --noinput --no-init-app

# RUN touch $file && chmod o+w ./website/templates/_log_templates.mako
# RUN touch $file && chmod o+w ./website/static/built/nodeCategories.json
#
# RUN rm ./website/settings/local.py
# RUN rm ./api/base/settings/local.py

# Copy the rest of the code over
COPY ./ ./

ARG GIT_COMMIT=
ENV GIT_COMMIT ${GIT_COMMIT}




CMD ["su-exec", "nobody", "invoke", "--list"]
