import sso


sso = sso.SSO()
login = sso.login()
if login:
    result = sso.create_user(user_json)
print(result)
if result.get("body").get("execution").get("status") == "incomplete":
    sso.create_zendesk_ticket(result)
