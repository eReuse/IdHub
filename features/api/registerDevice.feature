@Devices
Feature: Register Device to a DLT through the API

    Only an API user with the "Operator" credential can register a new Device
    to a DLT. Once a device is registered, a proof of it is created onto the target DLT.

    Scenario: A user with an invalid token registers a new Device
        Given an invalid API user
        And a new unique CHID
        When sends a Post request to the path "registerDevice" with the given parameters
        Then gets an error response with code 400
        And response error message "Invalid API token"
      