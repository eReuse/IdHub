@Devices
Feature: Generate a new generic proof into a DLT

    Only an API user with an "Operator" or "Witness" credential can issue a new generic proof of a Device
    into a DLT.

Background: Register a device into the DLT
        Given An issuer gives "Operator" credential to a valid API user
        And a new unique CHID
        And "The Operator" sends a Post request to the path "registerDevice" with the given parameters

Scenario: A valid API user with the Operator credential issues a new generic proof of an existing deviceCHID
        Given a DocumentID, DocumentSignature, IssuerID and a Type
        When "The Operator" sends a Post request to the path "generateProof" with the given parameters
        Then gets a response with code 201
        And the timestamp of the DLT when the operation was done

Scenario: A valid API user with the Operator credential issues a new generic proof of a non-existent deviceCHID
        Given a DocumentID, DocumentSignature, IssuerID and a Type
        And a new unique CHID
        When "The Operator" sends a Post request to the path "generateProof" with the given parameters
        Then gets an error response with code 400
        And response error message "CHID not registered"

Scenario: A valid API user with the Witness credential issues a new generic proof of an existing deviceCHID
        Given An issuer gives "Witness" credential to a valid API user
        And a DocumentID, DocumentSignature, IssuerID and a Type
        When "The Witness" sends a Post request to the path "generateProof" with the given parameters
        Then gets a response with code 201
        And the timestamp of the DLT when the operation was done

Scenario: A valid API user with the Witness credential issues a new generic proof of a non-existent deviceCHID
        Given An issuer gives "Witness" credential to a valid API user
        And a DocumentID, DocumentSignature, IssuerID and a Type
        And a new unique CHID
        When "The Witness" sends a Post request to the path "generateProof" with the given parameters
        Then gets an error response with code 400
        And response error message "CHID not registered"

Scenario: A valid API user without an Operator or Witness credential issues a new generic proof of an existing deviceCHID
        And a DocumentID, DocumentSignature, IssuerID and a Type
        And a valid API user
        When "The API user" sends a Post request to the path "generateProof" with the given parameters
        Then gets an error response with code 400
        And response error message "The user is not an owner, operator, or witness"

Scenario: An invalid API user issues a new generic proof of an existing deviceCHID
        Given a DocumentID, DocumentSignature, IssuerID and a Type
        And an invalid API user
        When "The invalid API user" sends a Post request to the path "generateProof" with the given parameters
        Then gets an error response with code 400
        And response error message "Invalid API token"
