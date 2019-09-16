
## Docker and OS Setup

1. Install the Docker Client
  - OSX: https://www.docker.com/products/docker#/mac
  - Ubuntu
    - docker: https://docs.docker.com/engine/installation/linux/ubuntulinux
    - docker-compose: https://docs.docker.com/compose/install/
  - Windows: https://www.docker.com/products/docker#/windows
2. Grant the docker client additional memory and cpu (minimum of 4GB and 2 CPU)
   - OSX: https://docs.docker.com/docker-for-mac/#/preferences
   - Ubuntu: N/A
   - Windows: https://docs.docker.com/docker-for-windows/#advanced
3. Setup the Operating System
  - OSX
    - Alias the loopback interface

    ```bash
    export libdir='/Library/LaunchDaemons' \
      && export file='com.runlevel1.lo0.192.168.168.167.plist' \
      && sudo cp $file $libdir \
      && sudo chmod 0644 $libdir/$file \
      && sudo chown root:wheel $libdir/$file \
      && sudo launchctl load $libdir/$file
    ```
  - Ubuntu
    - Add loopback alias
      `sudo ifconfig lo:0 192.168.168.167 netmask 255.255.255.255 up`

      - For persistance, add to /etc/network/interfaces...
        Add lo:0 to auto line...
        ```auto lo lo:0```
        Add stanza for lo:0...
        ```iface lo:0 inet static
               address 192.168.168.167
               netmask 255.255.255.255
               network 192.168.168.167
        ```
    - If UFW enabled. Enable UFW forwarding.
      - https://docs.docker.com/engine/installation/linux/linux-postinstall/#allow-access-to-the-remote-api-through-a-firewall
    - If needed. Configure a DNS server for use by Docker.
      - https://docs.docker.com/engine/installation/linux/linux-postinstall/#specify-dns-servers-for-docker
    - Configure docker to start at boot for Ubuntu 15.04 onwards
      `sudo systemctl enable docker`

    - In order to run OSF Preprints, raise fs.inotify.max_user_watches from default value
      `echo fs.inotify.max_user_watches=131072 | sudo tee -a /etc/sysctl.conf`
      `sudo sysctl -p`

  - Windows
    - Install Microsoft Loopback Adapter (Windows 10 follow community comments as the driver was renamed)
      https://technet.microsoft.com/en-us/library/cc708322(v=ws.10).aspx
    - Rename the new Loopback Interface (typically called 'Ethernet 2')
      - List interfaces

        `netsh interface show interface`
      - Rename the interface

        `netsh inteface set interface "Ethernet 2" newname="Loopback"`
      - Assign the Loopback interface an IP address

        `netsh interface ip add address "Loopback" 192.168.168.167 255.255.255.255`
      - Allow Docker to access to Drive your project is stored on

        Open the Docker Client -> Settings -> Shared Drives -> e.g. C -> Apply



## Application Configuration

* _NOTE: After making changes to `Environment Variables` or `Volume Mounts` you will need to recreate the container(s)._

  - `$ docker-compose up --force-recreate --no-deps preprints`

1. Application Settings
 - e.g. OSF & OSF API local.py

    `$ cp ./website/settings/local-dist.py ./website/settings/local.py`

    `$ cp ./api/base/settings/local-dist.py ./api/base/settings/local.py`

    `$ cp ./docker-compose-dist.override.yml ./docker-compose.override.yml`

2. OPTIONAL (uncomment the below lines if you will use remote debugging) Environment variables (incl. remote debugging)
  - e.g. .docker-compose.env

    ```bash
    WEB_REMOTE_DEBUG=192.168.168.167:11000
    API_REMOTE_DEBUG=192.168.168.167:12000
    WORKER_REMOTE_DEBUG=192.168.168.167:13000
    ```

      _NOTE: Similar docker-compose.\<name\>.env environment configuration files exist for services._

## Application Runtime

* _NOTE: Running docker containers detached (`-d`) will execute them in the background, if you would like to view/follow their console log output use the following command._

  - `$ docker-compose logs -f --tail 1000 web`

1. Application Environment

  - `$ docker-compose up requirements mfr_requirements wb_requirements`

    _NOTE: When the various requirements installations are complete these containers will exit. You should only need to run these containers after pulling code that changes python requirements or if you update the python requirements._

2. Start Core Component Services (Detached)
  - `$ docker-compose up -d elasticsearch postgres mongo rabbitmq`

3. Remove your existing node_modules and start the assets watcher (Detached)
  - `$ rm -Rf ./node_modules`
  - `$ docker-compose up -d assets`
  - `$ docker-compose up -d admin_assets`

    _NOTE: The first time the assets container is run it will take Webpack/NPM up to 15 minutes to compile resources.
    When you see the BowerJS build occurring it is likely a safe time to move forward with starting the remaining
    containers._
4. Start the Services (Detached)
  - `$ docker-compose up -d mfr wb fakecas sharejs`
5. Run migrations and create preprint providers
  - When starting with an empty database you will need to run migrations and populate preprint providers. See the [Running arbitrary commands](#running-arbitrary-commands) section below for instructions.
6. Start the OSF Web, API Server, Preprints, and Registries (Detached)
  - `$ docker-compose up -d worker web api admin preprints registries ember_osf_web`
7. View the OSF at [http://localhost:5000](http://localhost:5000).


## Quickstart: Running all OSF services in the background

- Once the requirements have all been installed, you can start the OSF in the background with

  ```bash
  $ docker-compose up -d assets admin_assets mfr wb fakecas sharejs worker web api admin preprints registries ember_osf_web
  ```

- To view the logs for a given container:

  ```bash
  $ docker-compose logs -f --tail 100 web
  ```

## Running arbitrary commands

- View logs: `$ docker-compose logs -f --tail 100 <container_name>`
    - _NOTE: CTRL-c will exit_
- Run migrations:
  - After creating migrations, resetting your database, or starting on a fresh install you will need to run migrations to make the needed changes to database. This command looks at the migrations on disk and compares them to the list of migrations in the `django_migrations` database table and runs any migrations that have not been run.
    - `docker-compose run --rm web python manage.py migrate`
- Populate institutions:
  - After resetting your database or with a new install you will need to populate the table of institutions. **You must have run migrations first.**
    - `docker-compose run --rm web python -m scripts.populate_institutions -e test -a`
- Populate preprint, registration, and collection providers:
  - After resetting your database or with a new install, the required providers and subjects will be created automatically **when you run migrations.** To create more:
    - `docker-compose run --rm web python manage.py populate_fake_providers`
- Populate citation styles
  - Needed for api v2 citation style rendering.
    - `docker-compose run --rm web python -m scripts.parse_citation_styles`
- Start ember_osf_web
  - Needed for quickfiles feature:
    - `docker-compose up -d ember_osf_web`
- OPTIONAL: Register OAuth Scopes
  - Needed for things such as the ember-osf dummy app
    - `docker-compose run --rm web python -m scripts.register_oauth_scopes`
- OPTIONAL: Create migrations:
  - After changing a model you will need to create migrations and apply them. Migrations are python code that changes either the structure or the data of a database. This will compare the django models on disk to the database, find the differences, and create migration code to change the database. If there are no changes this command is a noop.
    - `docker-compose run --rm web python manage.py makemigrations`
- OPTIONAL: Destroy and recreate an empty database:
  - **WARNING**: This will delete all data in your database.
    - `docker-compose run --rm web python manage.py reset_db --noinput`

## Application Debugging

### Catching Print Statements

If you want to debug your changes by using print statements, you'll have to have to set your container's environment variable PYTHONUNBUFFERED to 0. You can do this two ways:

  1. Edit your container configuration in docker-compose.mfr.env or docker-compose.mfr.env to include the new environment variable by uncommenting PYTHONUNBUFFERED=0
  2. If you're using a container running Python 3 you can insert the following code prior to a print statement:
   ```
    import functools
    print = functools.partial(print, flush=True)
   ```


### Console Debugging with IPDB

If you use the following to add a breakpoint

```python
import ipdb; ipdb.set_trace()
```

You should run the `web` and/or `api` container (depending on which codebase the breakpoint is in) using:

```bash
# Kill the already-running web container
$ docker-compose kill web

# Run a web container. App logs and breakpoints will show up here.
$ docker-compose run --rm --service-ports web
```

**IMPORTANT: While attached to the running app, CTRL-c will stop the container.** To detach from the container and leave it running, **use CTRL-p CTRL-q**. Use `docker attach` to re-attach to the container, passing the *container-name* (which you can get from `docker-compose ps`), e.g. `docker attach osf_web_run_1`.

### Remote Debugging with PyCharm

- Add a Python Remote Debugger per container
  - Name: `Remote Debug (web)`
  - Local host name: `192.168.168.167`
  - Port: `11000`
  - Path mappings: (It is recommended to use absolute path. `~/` may not work.)
    - `/Users/<your username>/Projects/cos/osf : /code`
    - (Optional) `/Users/<your username>/.virtualenvs/osf/lib/python2.7/site-packages : /usr/local/lib/python2.7/site-packages`
  - `Single Instance only`
- Configure `.docker-compose.env` `<APP>_REMOTE_DEBUG` environment variables to match these settings.

## Application Tests
- Run All Tests
  - `$ docker-compose run --rm web invoke test`

- Run OSF Specific Tests
  - `$ docker-compose run --rm web invoke test_osf`

- Test a Specific Module
  - `$ docker-compose run --rm web invoke test_module -m tests/test_conferences.py`

- Test a Specific Class
  - `docker-compose run --rm web invoke test_module -m tests/test_conferences.py::TestProvisionNode`

- Test a Specific Method
  - `$ docker-compose run --rm web invoke test_module -m tests/test_conferences.py::TestProvisionNode::test_upload`

- Test with Specific Parameters (1 cpu, capture stdout)
  - `$ docker-compose run --rm web invoke test_module -m tests/test_conferences.py::TestProvisionNode::test_upload -n 1 --params '--capture=sys'`

## Managing Container State

Restart a container:
  - `$ docker-compose restart -t 0 assets`

Recreate a container _(useful to ensure all environment variables/volume changes are in order)_:
  - `$ docker-compose up --force-recreate --no-deps assets`

Delete a container _(does not remove volumes)_:
  - `$ docker-compose stop -t 0 assets`
  - `$ docker-compose rm assets`

List containers and status:
  - `$ docker-compose ps`

### Backing up your database
In certain cases, you may wish to remove all docker container images, but preserve a copy of the database used by your
local OSF instance. For example, this is helpful if you have test data that you would like to use after
resetting docker. To back up your database, follow the following sequence of commands:

1. Install Postgres on your local machine, outside of docker. (eg `brew install postgres`) To avoid migrations, the
  version you install must match the one used by the docker container.
  ([as of this writing](https://github.com/CenterForOpenScience/osf.io/blob/ce1702cbc95eb7777e5aaf650658a9966f0e6b0c/docker-compose.yml#L53), Postgres 9.6)
2. Start postgres locally. This must be on a different port than the one used by [docker postgres](https://github.com/CenterForOpenScience/osf.io/blob/ce1702cbc95eb7777e5aaf650658a9966f0e6b0c/docker-compose.yml#L61).
  Eg, `pg_ctl -D /usr/local/var/postgres start -o "-p 5433"`
3. Verify that the postgres docker container is running (`docker-compose up -d postgres`)
4. Tell your local (non-docker) version of postgres to connect to (and back up) data from the instance in docker
  (defaults to port 5432):
  `pg_dump --username postgres --compress 9 --create --clean --format d --jobs 4 --host localhost --file ~/Desktop/osf_backup osf`

(shorthand: `pg_dump -U postgres -Z 9 -C --c -Fd --j 4 -h localhost --f ~/Desktop/osf_backup osf`)


#### Restoring your database
To restore a local copy of your database for use inside docker, make sure to start both local and dockerized postgres
(as shown above). For best results, start from a clean postgres container with no other data. (see below for
instructions on dropping postgres data volumes)

When ready, run the restore command from a local terminal:
```bash
$ pg_restore --username postgres --clean --dbname osf --format d --jobs 4 --host localhost ~/Desktop/osf_backup
```

(shorthand) `pg_restore -U postgres -c -d osf -Fd -j 4 -h localhost ~/Desktop/osf_backup`

## Cleanup & Docker Reset

Resetting the Environment:

  **WARNING: All volumes and containers are destroyed**
  - `$ docker-compose down -v`

Delete a persistent storage volume:

  **WARNING: All postgres data will be destroyed.**
  - `$ docker-compose stop -t 0 postgres`
  - `$ docker-compose rm postgres`
  - `$ docker volume rm osfio_postgres_data_vol`

## Updating

```bash
$ git stash # if you have any changes that need to be stashed
$ git pull upstream develop # (replace upstream with the name of your remote)
$ git stash pop # unstash changes
# If you get an out of space error
$ docker image prune
# Pull latest images
$ docker-compose pull

$ docker-compose up requirements mfr_requirements wb_requirements
# Run db migrations
$ docker-compose run --rm web python manage.py migrate
```

## Miscellaneous

### Runtime Privilege

When running privileged commands such as `strace` inside a docker container, you may encounter the following error.

```bash
strace: test_ptrace_setoptions_followfork: PTRACE_TRACEME doesn't work: Operation not permitted
```

The issue is that docker containers run in unprivileged mode by default.

For `docker run`, you can use `--privilege=true` to give the container extended privileges. You can also add or drop capabilities by using `cap-add` and `cap-drop`. Since Docker 1.12, there is no need to add `--security-opt seccomp=unconfined` because the seccomp profile will adjust to selected capabilities. ([Reference](https://docs.docker.com/engine/reference/run/#runtime-privilege-and-linux-capabilities))

When using `docker-compose`, set `privileged: true` for individual containers in the `docker-compose.yml`. ([Reference](https://docs.docker.com/compose/compose-file/#domainname-hostname-ipc-mac_address-privileged-read_only-shm_size-stdin_open-tty-user-working_dir)) Here is an example for WaterButler:

```yml
wb:
  image: quay.io/centerforopenscience/waterbutler:develop
  command: invoke server
  privileged: true
  restart: unless-stopped
  ports:
    - 7777:7777
  env_file:
    - .docker-compose.wb.env
  volumes:
    - wb_requirements_vol:/usr/local/lib/python3.5
    - wb_requirements_local_bin_vol:/usr/local/bin
    - osfstoragecache_vol:/code/website/osfstoragecache
    - wb_tmp_vol:/tmp
  stdin_open: true
```
