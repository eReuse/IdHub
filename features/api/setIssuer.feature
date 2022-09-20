@API_management
Feature: Set issuer credential to a User

    Admin gives issuing privileges to a API user. 

    Scenario: As admin, set issuer credential to a registered User
        Given an API admin user
        And a valid target user
        When sends a Post request to the path "setIssuer" with the given parameters
        Then gets a response with code 201
        And status "Success."
        And a get request to "checkUserRoles" of the target user returns true in the "isIssuer" camp

    Scenario: As admin, set issuer credential to a user not registered
        Given an API admin user 
        And an invalid target user
        When sends a Post request to the path "setIssuer" with the given parameters
        Then gets an error response with code 400
        And response error message "Target user doesnt exist."

    Scenario: As a user without admin privileges, set issuer credential to a registered User
        Given a valid API user
        And a valid target user
        When sends a Post request to the path "setIssuer" with the given parameters
        Then gets an error response with code 400
        And response error message "Need admin token."

