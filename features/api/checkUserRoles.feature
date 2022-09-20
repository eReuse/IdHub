@API_management
Feature: Check the roles of a a given API user.

    Scenario: Check roles of a valid API user
        Given a valid API user
        When sends a Post request to the path "checkUserRoles" with the given parameters
        Then gets a response with code 200
        And status "Success."
        And the user roles, all set to false

    Scenario: Check roles of an invalid API user
        Given an invalid API user
        When sends a Post request to the path "checkUserRoles" with the given parameters
        Then gets an error response with code 400
        And response error message "Invalid API token"