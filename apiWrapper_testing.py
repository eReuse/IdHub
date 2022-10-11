import apiWrapper
import json
from random import randint

#register_user(parameters, headers)
#res = apiWrapper.register_user("","ethereum")

#api1 = apiWrapper.API("http://localhost:3010","R6M53rSFWj6iIWD.RYCb1Wmifw4VdfX4UHsnU40kYm1IzE40tcmkgDiRpwCnS6mw9u5yrK1jS0R89FYV","ethereum")

#res = api1.check_user_roles()
#print(res)

#getting users & admin api keys
#needs an json file "adminToken.json" at path with "admin_token" key
f = open("./features/api/adminToken.json")
adminJson = json.load(f)

keyUser1 = apiWrapper.register_user("http://localhost:3010", "")['data']['api_token']
keyUser2 = apiWrapper.register_user("http://localhost:3010", "")['data']['api_token']

apiUser1 = apiWrapper.API("http://localhost:3010",keyUser1,"ethereum")
apiUser2 = apiWrapper.API("http://localhost:3010",keyUser2,"ethereum")
apiadmin = apiWrapper.API("http://localhost:3010",adminJson['admin_token'],"ethereum")

targetUser1 = keyUser1[ 0 : 15 ]
targetUser2 = keyUser2[ 0 : 15 ]

#random deviceCHID generator
chid = str(randint(0,9999))
chiddpp =  chid + ":111"

#admin sets issuer credential to user1
print(apiadmin.set_issuer(targetUser1))

#user1 checks his roles
print("user1 user roles:")
print(apiUser1.check_user_roles())

#user1 gives operator credential to user2
print("user1 gives Operator role to user2:")
print(apiUser1.issue_credential("Operator", targetUser2))

#user1 tries to register device
print("user1 tries to register device")
print(apiUser1.register_device(chid))

#user2 registers device
print("user2 registers device")
print(apiUser2.register_device(chid))

#user2 queries register device
print("user2 queries register device")
print(apiUser2.get_register_proof(chid))

#user2 issues new device passport
print("user 2 issues new device passport")
print(apiUser2.issue_passport(chiddpp + ":dpp", "docid", "docsig", "issuerid"))

#user2 queries issuing proofs
print("user2 queries issuing proofs")
print(apiUser2.get_issue_proofs(chid))

#user2 generates generic proof
print("user2 generates generic proof")
print(apiUser2.generate_proof(chid, "docid", "docsig", "issuerid", "type1"))

#user2 queries generic proofs
print("user2 queries generic proofs")
print(apiUser2.get_generic_proofs(chid))

#user2 deregisters device
print("user2 deregisters device")
print(apiUser2.deRegister_device(chid))

#user2 gets deregister proof
print("user2 gets deregister proof")
print(apiUser2.get_deregister_proofs(chid))

#print(key['data']['api_token'])
#print(key2.api_token)

#res = apiWrapper.invalidate_user("OxnALFRdGF3Xfwf.uB4ktRldZB6QIYqjjPXg18IWbP1FPRnvXVjGHBqhodR7NLQpqeO7bntrVywJjbWV","ethereum")
#print (res.content)