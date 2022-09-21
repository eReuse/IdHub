@Devices
Feature: deRegister Device of a DLT through the API

    Only an API user with the "Operator" credential can deRegister a new Device
    to a DLT. Once a device is deRegistered, a proof of it is created onto the target DLT.

Rule: Users can only deregister a device if they have an Operator credential and the device exists on the DLT

    Background: 
        Given An issuer gives "Operator" credential to a valid API user
        And a new unique CHID
        And "The Operator" sends a Post request to the path "registerDevice" with the given parameters

Scenario: A valid API user with the Operator credential deregisters an existing device
        When "The Operator" sends a Post request to the path "deRegisterDevice" with the given parameters
        Then gets a response with code 201
        And the timestamp of the DLT when the operation was done

Scenario: A valid API user with the Operator credential deregisters a non-existent device
        Given a new unique CHID
        When "The Operator" sends a Post request to the path "deRegisterDevice" with the given parameters
        Then gets an error response with code 400
        And response error message "CHID not registered"

Scenario: A valid API user without the Operator credential deregisters an existing device
        Given a valid API user
        And a new unique CHID
        When "The valid API user" sends a Post request to the path "deRegisterDevice" with the given parameters
        Then gets an error response with code 400
        And response error message "CHID not registered"

Scenario: An invalid API user deregisters an existing device
        Given an invalid API user
        When "The invalid API user" sends a Post request to the path "deRegisterDevice" with the given parameters
        Then gets an error response with code 400
        And response error message "Invalid API token"

