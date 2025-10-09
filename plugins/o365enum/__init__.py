import utils.utils as utils


def validate(pluginargs, args):
    pluginargs = {
        'url' : "https://login.microsoftonline.com",
        'userenum' : True
    }
    return True, None, pluginargs


def testconnect(pluginargs, args, api, useragent):

    success = True
    headers = {
        'User-Agent' : useragent,
    }

    headers = utils.add_custom_headers(pluginargs, headers)

    resp = api.get("/common/GetCredentialType", headers=headers)

    if resp.status_code == 504:
        output = "Testconnect: Connection failed, endpoint timed out, exiting"
        success = False
    else:
        output = "Testconnect: Connection success, continuing"

    return success, output, pluginargs
