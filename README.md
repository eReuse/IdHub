# IdHub

IdHub is a Django-based project designed to provide efficient identity management solutions.This README offers an overview of the project, setup instructions, and additional resources.

## About IdHub

The idHub service facilitates organisations (acting as issuer or verifiers) and beneficiaries (acting as subjects and credential holders) to issue, exchange, and verify data in the form of verifiable credentials for credible and flexible access to benefits or services.

## Features

The main modules components it provides:
- **Admin Dashboard**: A user-friendly admin panel that enables administrator to manage users and roles, handle aspects such as the creation of organisational Decentralized Identifiers (DIDs), credentials issued by the organisation, and upload the information for issuance of credentials to users (including credential schemas and data).
- **User Dashboard**: A user-friendly user panel equips users to manage their personal information, create an identity (DID), request the issuance of a credential, and present these credentials to entities within our user communitity. This module operates as a user wallet.
The application's backend is responsible for issuing credentials upun user request through the user module. Meanwhile, the idHub can function as a credential verifier and engage in dialogues with other idHub instances that operate as user wallets by implementing a OIDC4VP based dialog. Consequently, the idHub is multifaceted, capable of functioning as an issuer, wallet or verifier.
- **OIDC4VP module**: Module where all oidc4vp flows reside for credential presentation.

## Getting Started

### Prerequisites

- Python >= 3.11.2

### Installation

1. Clone this repository: 
   ```
   git clone https://gitea.pangea.org/trustchain-oc1-orchestral/IdHub
   ```
2. (Recommended but optional) Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate
   ```
3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```
   python manage.py migrate
   ```
5. Optionally you can install a minumum data set:
   ```
   python manage.py initial_datas
   ```
6. Start the development server:
   ```
   python manage.py runserver
   ```

### Configuration

Below you can find a sample .env file with the required variables and a descriptive comment.

If you wish to test the application, you can paste the text below into a `.env` file.
Note that these values are insecure and should not be used in a production environment.
```
# Django secret key. 
# It is used for cryptographic signing, securing password reset tokens, CSRF protection, and cookie security, ensuring the integrity and confidentiality of critical security operations within a Django application.
# As the name implies, it's critical that this is kept secret in a production environment.
SECRET_KEY = 'Dummy-S3cr3t-K3y!#12#**3aaxd'

# Enables Django's debug mode, providing detailed error pages and diagnostic information for development purposes.
DEBUG=True

# Specifies a list of host/domain names that this Django site can serve, enhancing security by preventing HTTP Host header attacks.
ALLOWED_HOSTS=.localhost,127.0.0.1

# Defines a list of trusted origins for safe cross-site HTTP requests, aiding in the prevention of cross-site request forgery attacks.
CSRF_TRUSTED_ORIGINS="http://localhost:8000","http://127.0.0.1:8000","http://localhost"

# Designates the file system path where static files will be collected and stored, used for serving static files in a production environment.
STATIC_ROOT=/tmp/static/

# Sets the file system path for storing uploaded media files from users, such as images and documents.
MEDIA_ROOT=/tmp/media/

# Typically used for specifying the database connection info in a single environment variable, but Django itself uses database settings defined in its settings.py.
# Currently unused but will be used in the future
# DATABASE_URL=postgres://link:to@database:port/idhub

# Defines the admin user after running the initial_datas command
# Defaults to "admin@example.org" if no INITIAL_ADMIN_EMAIL is provided
# INITIAL_ADMIN_EMAIL="idhub_admin@pangea.org"

# Configures a list of tuples containing names and email addresses of site administrators who should receive error notifications.
ADMINS=[('Admin', 'admin@example.org')]

# Specifies a list of individuals who will get emailed for broken link notifications if BrokenLinkEmailsMiddleware is enabled.
MANAGERS=[('Manager', 'manager@example.org')]

DOMAIN="localhost"

# Determines the default email address to use for automated correspondence from the Django application.
DEFAULT_FROM_EMAIL="idhub_noreply@pangea.org"

# Set the host, username, password, and port with which to establish an SMTP connection
EMAIL_HOST="mail.pangea.org"
EMAIL_HOST_USER="idhub_noreply"
EMAIL_HOST_PASSWORD="p4ssw0rd!"
EMAIL_PORT=587

# Enables Transport Layer Security (TLS) for secure email delivery when connecting to the SMTP server.
EMAIL_USE_TLS=True

# Specifies Django's email backend for sending emails through an SMTP server.
EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"

# Defines the directory in which to save emails that Django sends in development mode.
EMAIL_FILE_PATH="/tmp/app-messages"

# Sets the time zone for datetime operations and as the default time zone for users.
TIME_ZONE='Europe/Madrid'

# Determines where the user is redirected after a verification.
# If this variable is commented out or missing, redirection after verification will be disabled
RESPONSE_URI="http://localhost:8000/oidc4vp/"

# Used for communication with a secondary IdHub that acts as wallet from a page that requests verification
# Determines where the verifiers' endpoint will be
ALLOW_CODE_URI="http://localhost:8000/allow_code"

# Used for communication with a secondary IdHub that acts as wallet from a page that requests verification
# Determines which credential types will be supported for verification
SUPPORTED_CREDENTIALS=['Membership Card']

# Determines the name of the credentials emitted by the IdHub application
ORGANIZATION="Pangea"

# Enables the sending of emails throughout the application.
# If disabled, all emails sent from application usage will be printed instead.
ENABLE_EMAIL=false

# Used to determine whether or not the application will enforce 2FA. Its recommended value is `true` for production environments.
# This requires that the `EMAIL_` related variables are properly configured.
ENABLE_2FACTOR_AUTH=false
```

### Usage

Access the application at `http://localhost:8000`.

### Running Tests

IdHub uses Django's built-in testing tools to ensure the reliability and performance of the application. Follow these steps to run the tests:

Execute the following command in your project directory to run all tests:

```
python manage.py test
```

This command will discover and run all tests in the `tests` directories of the application.

## Repository Structure

IdHub's repository is organized into several directories, each serving a specific purpose in the project:

- **examples**: Examples of different data files used in some functionalities.

- **idhub**: The core directory of the IdHub project (templates, forms, views, models, etc.). It includes the main functionality of this Django project.

- **idhub_auth**: This directory contains the module where the users and the data encryption/decryption system are defined.

- **locale**: Contains localization files for IdHub (po and mo files for translations), enabling support for multiple languages.

- **oidc4vp**: Module where all oidc4vp flows (implementation of the credential's presentation dialog) reside.

- **promotion**: Example module showing how to create a portal that initializes the oidc4vp flow.

- **schemas**: Contains verifiable credential schemas used within IdHub for a preload without having to go to the original source. 

- **trustchain_idhub**: This folder includes settings and configurations for the Django project. It is the entry point of Django, where the global variables, the startup files and the file that defines the endpoints are defined.

- **utils**: A utility folder containing various helper scripts and tools developed by us but that are independent of idHub. Even so, IdHub uses them and needs them (examples of this are the validation system for the data that is loades by excel, or the system that manages the sskit)

## Webhook
You need define a token un the admin section "/webhool/tokens"
For define one query here there are a python example:
```
   import requests
   import json

   url = "https://api.example.com/webhook/verify/"
   data = {
      "type": "credential",
      "data": {
         '@context': ['https://www.....
      }

   headers = {
      "Authorization": f"Bearer {token}",
      "Content-Type": "application/json"
   }

   response = requests.post(url, headers=headers, data=json.dumps(data))

   response.status_code == 200
   response.json()
   
```
   The response of verification can be ```{'status': 'success'}``` or ```{'status': 'fail'}```
   If no there are *type* in data or this is not a *credential* then, the verification proccess hope a *presentation*
   The field *data* have the credential or presentation.

## Documentation

For detailed documentation, visit [Documentation Link](http://idhub.pangea.org/help/).

## License

This project is licensed under the GNU Affero General Public License - see the [LICENSE.md](LICENSE.md) file for details.

