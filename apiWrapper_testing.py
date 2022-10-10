import apiWrapper

#register_user(parameters, headers)
#res = apiWrapper.register_user("","ethereum")


api1 = apiWrapper.API("http://localhost:3010","R6M53rSFWj6iIWD.RYCb1Wmifw4VdfX4UHsnU40kYm1IzE40tcmkgDiRpwCnS6mw9u5yrK1jS0R89FYV","ethereum")

res = api1.check_user_roles()
print(res)


# key = apiWrapper.register_user("http://localhost:3010", "")
# print(key.content)

#res = apiWrapper.invalidate_user("OxnALFRdGF3Xfwf.uB4ktRldZB6QIYqjjPXg18IWbP1FPRnvXVjGHBqhodR7NLQpqeO7bntrVywJjbWV","ethereum")
#print (res.content)