import utils.utils as utils


def validate(pluginargs, args):
    #
    # Plugin Args
    #
    # --url https://ping.domain.com   ->  Ping target
    #
    if "url" in pluginargs.keys():
        return True, None, pluginargs
    else:
        error = "Missing url, specify as --url https://ping.domain.com"
        return False, error, None


def testconnect(pluginargs, args, api, useragent):

    success = True
    headers = {
        "User-Agent" : useragent,
    }

    headers = utils.add_custom_headers(pluginargs, headers)

    resp = api.get(headers=headers)

    if resp.status_code == 504:
        output = "Testconnect: Connection failed, endpoint timed out, exiting"
        success = False
    else:
        output = "Testconnect: Connection success, continuing. WARNING - This plugin is in beta and has not been rigorously tested!"

    return success, output, pluginargs
