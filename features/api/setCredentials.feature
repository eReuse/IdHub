@API_management
Feature: Set Operator, witness and verifier to users

    Scenario: Give Operator credential to an API user as an Issuer
        Given a valid API user with an issuer credential
        And a valid target user
        When issuer user sends a Post request to the path "issueCredential" with "Operator" credential to the target user
        Then gets a response with code 201
        And status "Success."
        And a get resquest to "checkUserRoles" of the target user returns true in the "isOperator" camp

    Scenario: Give Verifier credential to an API user as an Issuer
        Given a valid API user with an issuer credential
        And a valid target user
        When issuer user sends a Post request to the path "issueCredential" with "Verifier" credential to the target user
        Then gets a response with code 201
        And status "Success."
        And a get resquest to "checkUserRoles" of the target user returns true in the "isVerifier" camp

    Scenario: Give Witness credential to an API user as an Issuer
        Given a valid API user with an issuer credential
        And a valid target user
        When issuer user sends a Post request to the path "issueCredential" with "Witness" credential to the target user
        Then gets a response with code 201
        And status "Success."
        And a get resquest to "checkUserRoles" of the target user returns true in the "isWitness" camp
