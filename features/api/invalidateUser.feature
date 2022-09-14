@API_management
Feature: Invalidate User to the API

    User invalidates itself from using the API (deletes it's storage entry)

    Scenario: Invalidate user with a valid token
        Given a valid API user
        When sends a Post request to the path "invalidateUser" with the given parameters
        Then gets a response with code 200
        And status "Success."
        And the deleted token

    Scenario: Invalidate user with an invalid token
        Given an invalid API user
        When sends a Post request to the path "invalidateUser" with the given parameters
        Then gets an error response with code 400
        And response error message "Invalid API token"
        