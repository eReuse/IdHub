@API_management
Feature: Set issuer credential to a User

    Scenario: As admin, set issuer credential to a registered User
        Given an admin token and a target user
        When sends a Post request to the path "setIssuer" with target user token and admin token
        Then gets a response with code 201
        And status "Success."

    # Scenario: As admin, set issuer credential to a user not registered
    #     When sends a Post request to the path "registerUser" without ethereum privkey
    #     Then gets a response with code 201
    #     And status "Success."
    #     And a valid api_token, ethereum_keypar and iota_id

    # Scenario: As a user without admin privileges, set issuer credential to a registered User
    #     When sends a Post request to the path "registerUser" without ethereum privkey
    #     Then gets a response with code 201
    #     And status "Success."
    #     And a valid api_token, ethereum_keypar and iota_id

