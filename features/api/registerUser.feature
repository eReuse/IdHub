@API_management
Feature: Register User to the API

    The API needs to store DLT-specific information that helps identify
    each API user towards the supported DLTs. Therefore, any API endpoint
    that interacts with any DLT needs to be called through an registered API user.
    This feature validates registering an User with and without a specified ethereum privkey.


    Scenario: RegisterUser without ethereum privkey
        When sends a Post request to the path "registerUser" without parameters
        Then gets a response with code 201
        And status "Success."
        And a valid api_token, ethereum_keypar and iota_id

    Scenario: RegisterUser with a valid ethereum privkey
        Given a user with a randomly generated ethereum privkey
        When sends a Post request to the path "registerUser" with the given parameters
        Then gets a response with code 201
        And status "Success."
        And a valid api_token, the given ethereum_keypar and iota_id

    Scenario: RegisterUser with an invalid ethereum privkey
        Given a user with an invalid ethereum privkey
        When sends a Post request to the path "registerUser" with the given parameters
        Then gets an error response with code 400
        And response error message "Invalid PrivateKey format"