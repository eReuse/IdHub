@API_management
Feature: Invalidate User to the API

    User is invalidated from using the API.

    Scenario: Invalidate user with a valid token
        Given a valid API user
        When sends a Post request to the path "invalidateUser" with a valid token
        Then gets a response with code 200
        And status "Success."
        And the deleted token

    Scenario: Invalidate user with an invalid token
        Given a valid API user
        When sends a Post request to the path "invalidateUser" with an invalid token
        Then gets a response with code 400
        #And status "Success."
        #And the deleted token