
def require(val, message = ""):
    if not val:
        raise Exception(message)

