# Device Hub

DeviceHub is an IT Asset Management System focused on reusing devices, created under the [eReuse.org](https://www.ereuse.org) project.

## Overview

DeviceHub aims to:

- Provide a common IT Asset Management platform for donors, receivers, and IT professionals.
- Automatically collect, analyze, and share device metadata while ensuring privacy and traceability.
- Integrate with existing IT Asset Management Systems.
- Operate in a decentralized manner.

DeviceHub primarily works with three types of objects:

1. **Devices**: Including computers, smartphones, and their components.
2. **Events**: Actions performed on devices (e.g., Repair, Allocate).
3. **Accounts**: Users who perform events on devices.

## Installation

Assuming a host with debian stable

### Quickstart

For a quick start with dummy data in localhost, DeviceHub can be run directly with docker. To do so, from the root of the project run:

```bash
./docker-reset.sh
```

Note that everytime you perform the `docker-reset.sh` script, all data is lost.

Also there is a demo running in http://demo.ereuse.org/. The token for accessing the instance will be always: `token=5018dd65-9abd-4a62-8896-80f34ac66150`, but the instance will be reset every day at 4 am.

For production needs, review and change .env file properly

## Running from baremetal

### Prerequisites

- Python 3.10
- pip
- virtualenv

Specially when developing, is quite convenient to run DeviceHub from a virtual environment. To start with this deployment, create a virtual environment to isolate our project dependencies:

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### System Dependencies

#### Xapian

Now, install the xapian dependencies (xapian library and python bindings)

```bash
sudo apt-get install python3-xapian libxapian-dev
```

Allow the virtual environment to use system-installed packages:

```bash
export PYTHONPATH="${PYTHONPATH}:/usr/lib/python3/dist-packages"
```

#### Environment Variables

Now, configure the environment variables. For this, we will expand a `.env` file. You can use the following content as an example:

```source
STATIC_ROOT=/tmp/static/
MEDIA_ROOT=/tmp/media/
ALLOWED_HOSTS=localhost,localhost:8000,127.0.0.1,
DOMAIN=localhost
DEBUG=True
```

Now, expand the environment variables:

```bash
source .env
```

### Migrations

Now, apply migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

Also, we can add some dummy data into the database to play along:

```bash
python manage.py add_institution Pangea
python manage.py add_user Pangea user@example.org 1234
python manage.py up_snapshots example/snapshots/ user@example.org
```

### Run DeviceHub

Finally, we can run the DeviceHub service by running:

```bash
python manage.py runserver
```

### Clean up

To clean up the deployment and start fresh, just delete Django's database:

```bash
rm db/*
```

## License

DeviceHub is released under the [GNU Affero General Public License v3.0](LICENSE).
