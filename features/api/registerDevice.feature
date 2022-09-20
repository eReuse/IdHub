@Devices
Feature: Register Device to a DLT through the API

    Only an API user with the "Operator" credential can register a new Device
    to a DLT. Once a device is registered, a proof of it is created onto the target DLT.

Rule: Either if you are a valid or an invalid API user, it is not possible to register a new device without an Operator Credential

Scenario: A valid API user without the Operator credential registers a new device with a new unique DeviceCHID
        Given a valid API user
        And a new unique CHID
        When sends a Post request to the path "registerDevice" with the given parameters
        Then gets an error response with code 400
        And response error message "The user is not an operator"

Scenario: An invalid API user registers a new device with a new unique device CHID
        Given an invalid API user
        And a new unique CHID
        When sends a Post request to the path "registerDevice" with the given parameters
        Then gets an error response with code 400
        And response error message "Invalid API token"

Rule: Users can only register a new device if they have an Operator credential and a new unique DeviceCHID to register

    Background: 
        Given An issuer gives Operator credential to a valid API user

Scenario: A valid API user with the Operator credential registers a new device with a new unique DeviceCHID
        #Given An issuer gives Operator credential to a valid API user
        And a new unique CHID
        When sends a Post request to the path "registerDevice" with the given parameters
        Then gets a response with code 201
        And the registered device address on ethereum

Scenario: A valid API user with the Operator credential registers a new device with a duplicated DeviceCHID
        #Given An issuer gives Operator credential to a valid API user
        And The Operator registers a device with a new unique CHID
        When sends a Post request to the path "registerDevice" with the same CHID
        Then gets an error response with code 400
        And response error message "Device already exists"

Scenario: A valid API user with the Operator credential registers a new device without a DeviceCHID
        #Given An issuer gives Operator credential to a valid API user
        And an empty CHID
        When sends a Post request to the path "registerDevice" with the given parameters
        Then gets an error response with code 400
        And response error message "Invalid Syntax."

Scenario: A valid API user without the Operator credential registers a new device with a duplicated DeviceCHID
        #Given An issuer gives Operator credential to a valid API user
        And The Operator registers a device with a new unique CHID
        And a valid API user
        When sends a Post request to the path "registerDevice" with the same CHID
        Then gets an error response with code 400
        And response error message "Device already exists"