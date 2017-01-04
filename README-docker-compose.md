
## Docker and OS Setup

1. Install the Docker Client
  - OSX: https://www.docker.com/products/docker#/mac
  - Windows: https://www.docker.com/products/docker#/windows
2. Grant the docker client additional memory and cpu (minimum of 4GB and 2 CPU)
   - OSX: https://docs.docker.com/docker-for-mac/#/preferences
   - Windows: https://docs.docker.com/docker-for-windows/#advanced
3. Setup the Operating System
  - OSX
    - Alias the loopback interface

      `$ sudo cp com.runlevel1.lo0.192.168.168.167.plist /Library/LaunchDaemons`
      `$ sudo chmod 0644 /Library/LaunchDaemons/com.runlevel1.lo0.192.168.168.167.plist`
      `$ sudo chown root:wheel /Library/LaunchDaemons/com.runlevel1.lo0.192.168.168.167.plist`
      `$ sudo launchctl load /Library/LaunchDaemons/com.runlevel1.lo0.192.168.168.167.plist`

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
1. Application Settings
 - e.g. OSF & OSF API local.py

    `$ cp ./website/settings/local-dist.py ./website/settings/local.py`
    `$ cp ./api/base/settings/local-dist.py ./api/base/settings/local.py`

2. Environment variables (incl. remote debugging)
  - e.g. .docker-compose.env

    ```bash
    WEB_REMOTE_DEBUG=192.168.168.167:11000
    API_REMOTE_DEBUG=192.168.168.167:12000
    WORKER_REMOTE_DEBUG=192.168.168.167:13000
    ```

      _NOTE: Similar docker-compose.\<name\>.env environment configuration files exist for services._

3. Mounting Service Code
  - By modifying the docker-compose.override.yml file you can specify the relative path to your service code directory. e.g.
    - This makes it so your local changes will be reflected in the docker container. Until you do this none of your changes will have any effect.

    ```yml
    services:
      wb:
        volumes:
          - ../waterbutler/:/code
    ```

## Application Runtime
1. Application Environment

  - `$ docker-compose up requirements requirements_mfr requirements_wb`

    _NOTE: When the various requirements installations are complete these containers will exit. You should only need to run these containers after pulling code that changes python requirements or if you update the python requirements._

2. Start Core Component Services
  - `$ docker-compose up elasticsearch postgres tokumx`

3. Start the Assets Watcher
  - `$ docker-compose up assets`

    _NOTE: The first time the assets container is run it will take Webpack/NPM up to 15 minutes to compile resources.
    When you see the BowerJS build occurring it is likely a safe time to move forward with starting the remaining
    containers._
4. Start the Services
  - `$ docker-compose up mfr wb fakecas`
5. Run migrations and create preprint providers
  - When starting with an empty database you will need to run migrations and populate preprint providers. See the [Running arbitrary commands](#running-arbitrary-commands) section below for instructions.
6. Start the OSF Web and API Servers
  - `$ docker-compose up web api`

## Running arbitrary commands
- Run migrations:
  - After creating migrations, resetting your database, or starting on a fresh install you will need to run migrations to make the needed changes to database. This command looks at the migrations on disk and compares them to the list of migrations in the `django_migrations` database table and runs any migrations that have not been run.
    - `docker-compose run --no-deps web python manage.py migrate`
- Populate preprint providers:
  - After resetting your database or with a new install you will need to populate the table of preprint providers. **You must have run migrations first.**
    - `docker-compose run web python -m scripts.populate_preprint_providers`
- Create migrations:
  - After changing a model you will need to create migrations and apply them. Migrations are python code that changes either the structure or the data of a database. This will compare the django models on disk to the database, find the differences, and create migration code to change the database. If there are no changes this command is a noop.
    - `docker-compose run --no-deps web python manage.py makemigrations`
- Destroy and recreate an empty database:
  - **WARNING**: This will delete all data in your database.
    - `docker-compose run --no-deps web python manage.py reset_db --noinput`

## Application Debugging
- Console Debugging with IPDB
  - `docker attach [projectname]_web_1`

    _NOTE: You can detach from a container and leave it running using the CTRL-p CTRL-q key sequence._
- Remote Debugging with PyCharm
  - Add a Python Remote Debugger per container
    - Name: Remote Debug (web)
    - Local host name: 192.168.168.167
    - Port: 11000
    - Path mappings:
      - /Users/\<whoami\>/Projects/cos/osf : /code
      - /Users/\<whoami\>/.virtualenvs/osf/lib/python2.7/site-packages : /usr/local/lib/python2.7/site-packages
    - Single Instance only
  - Configure .docker-compose.env REMOTE_DEBUG environment variables to match settings.

## Cleanup & Docker Reset
- Resetting the Environment

  _**WARNING**: All volumes and containers are destroyed_
  - `$ docker-compose down -v`


- Delete a persistent storage volume

  _**WARNING**: All postgres data will be destroyed._
  - `$ docker-compose stop -t 0 postgres`
  - `$ docker-compose rm postgres`
  - `$ docker volume rm [projectname]_postgres_vol`
