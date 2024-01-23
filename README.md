# IdHub

IdHub is a Django-based project designed to provide efficient identity management solutions.This README offers an overview of the project, setup instructions, and additional resources.

## About IdHub

The idHub service, which facilitates organisations (acting as issuer or verifiers) and beneficiaries (acting as subjects and credential holders) to issue, exchange, and verify data in the form of verifiable credentials for credible and flexible access to benefits or services.

## Features

The main modules components it provides:
- **Admin Dashboard**: A user-friendly admin panel that enables administrator to manage users and roles, handle aspects such as the creation of organisational Decentralized Identifiers (DIDs), credentials issued by the organisation, and upload the information for issuance of credentials to users (including credential schemas and data).
- **User Dashboard**: A user-friendly user panel equips users to manage their personal information, create an identity (DID), request the issuance of a credential, and present these credentials to entities within our user communitity. This module operates as a user wallet.
The application's backend is responsible for issuing credentials upun user request through the user module. Meanwhile, the idHub can function as a credential verifier and engage in dialogues with other idHub instances that operate as user wallets by implementing a OIDC4VP based dialog. Consequently, the idHub is multifaceted, capable of functioning as an issuer, wallet or verifier.
- **OIDC4VP module**: Module where all oidc4vp flows reside for credential presentation.

## Getting Started

### Prerequisites

- Python 3.x

### Installation

1. Clone this repository: 
   ```
   git clone [FINAL IdHub repository LINK]
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

## Documentation

For detailed documentation, visit [Documentation Link](http://idhub.pangea.org/help/).

## License

This project is licensed under the GNU Affero General Public License - see the [LICENSE.md](LICENSE.md) file for details.

## Further Reading

- ...
