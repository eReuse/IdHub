@API_management
Feature: Set Operator, Witness and Verifier credentials to users

    Scenario: Give Operator credential to an API user as an Issuer
        Given a valid API user with an issuer credential
        And a valid target user
        When issuer user sends a Post request to the path "issueCredential" with "Operator" credential to the target user
        Then gets a response with code 201
        And status "Success."
        And a get request to "checkUserRoles" of the target user returns true in the "isOperator" camp

    Scenario: Give Verifier credential to an API user as an Issuer
        Given a valid API user with an issuer credential
        And a valid target user
        When issuer user sends a Post request to the path "issueCredential" with "Verifier" credential to the target user
        Then gets a response with code 201
        And status "Success."
        And a get request to "checkUserRoles" of the target user returns true in the "isVerifier" camp

    Scenario: Give Witness credential to an API user as an Issuer
        Given a valid API user with an issuer credential
        And a valid target user
        When issuer user sends a Post request to the path "issueCredential" with "Witness" credential to the target user
        Then gets a response with code 201
        And status "Success."
        And a get request to "checkUserRoles" of the target user returns true in the "isWitness" camp

    Scenario: Give Operator credential to an API user as not an Issuer
        Given a valid API user
        And a valid target user
        When issuer user sends a Post request to the path "issueCredential" with "Operator" credential to the target user
        Then gets an error response with code 400
        And response error message "Only usable by current Trust Anchor or an Issuer account"

    Scenario: Give Operator credential to an invalid API user as an Issuer
        Given a valid API user with an issuer credential
        And an invalid target user
        When issuer user sends a Post request to the path "issueCredential" with "Operator" credential to the target user
        Then gets an error response with code 400
        And response error message "Target user doesn't exist."
