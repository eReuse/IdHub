@Devices
Feature: Issue a new Device Passport (DPP) of a device into the DLT

    Only an API user with an "Operator" or "Witness" credential can issue a new Passport of a Device
    into a DLT. Once the passport is issued, a proof of it is created onto the target DLT.

Background: Register a device into the DLT
        Given An issuer gives "Operator" credential to a valid API user
        And a new unique CHID
        And "The Operator" sends a Post request to the path "registerDevice" with the given parameters

Scenario: A valid API user with the Operator credential issues a new DPP with a correct DPP format
        Given a correct DPP that contains an existent CHID
        And a DocumentID, DocumentSignature, IssuerID
        When "The Operator" sends a Post request to the path "issuePassport" with the given parameters
        Then gets a response with code 201
        And the timestamp of the DLT when the operation was done

Scenario: A valid API user with the Operator credential issues a new DPP with an incorrect DPP format
        Given an incorrect DPP
        And a DocumentID, DocumentSignature, IssuerID
        When "The Operator" sends a Post request to the path "issuePassport" with the given parameters
        Then gets an error response with code 400
        And response error message "Incorrect DPP format"

Scenario: A valid API user with the Witness credential issues a new DPP with a correct DPP format
        Given An issuer gives "Witness" credential to a valid API user
        And a correct DPP that contains an existent CHID
        And a DocumentID, DocumentSignature, IssuerID
        When "The Witness" sends a Post request to the path "issuePassport" with the given parameters
        Then gets a response with code 201
        And the timestamp of the DLT when the operation was done

Scenario: A valid API user with the Witness credential issues a new DPP with an incorrect DPP format
        Given An issuer gives "Witness" credential to a valid API user
        And an incorrect DPP
        And a DocumentID, DocumentSignature, IssuerID
        When "The Witness" sends a Post request to the path "issuePassport" with the given parameters
        Then gets an error response with code 400
        And response error message "Incorrect DPP format"

Scenario: A valid API user with the Operator credential issues a new DPP with a correct DPP format that does not contain an existent DeviceCHID
        Given a correct DPP that does not contain an existent CHID
        And a DocumentID, DocumentSignature, IssuerID
        When "The Operator" sends a Post request to the path "issuePassport" with the given parameters
        Then gets an error response with code 400
        And response error message "CHID not registered"

Scenario: A valid API user without an Operator or Witness credential issues a new DPP with a correct DPP format
        Given a correct DPP that contains an existent CHID
        And a DocumentID, DocumentSignature, IssuerID
        And a valid API user
        When "The API user" sends a Post request to the path "issuePassport" with the given parameters
        Then gets an error response with code 400
        And response error message "The message sender is not an owner, operator or witness"

Scenario: An invalid API user issues a new DPP with a correct DPP format 
        Given an invalid API user
        And a correct DPP that contains an existent CHID
        #And a DocumentID, DocumentSignature, IssuerID
        When "The invalid API user" sends a Post request to the path "issuePassport" with the given parameters
        Then gets an error response with code 400
        And response error message "Invalid API token"

