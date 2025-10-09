import utils.utils as utils


def validate(pluginargs, args):
    #
    # Plugin Args
    #
    # --url https://domain.com    ->  gives the URL to the application
    # --domain DOMAIN              ->  Optional Input domain name
    #
    if 'url' in pluginargs.keys():
        if "https://" not in pluginargs['url'] and "http://" not in pluginargs['url']:
            error = "URL requires http:// or https:// prefix"
            return False, error, None
        return True, None, pluginargs
    else:
        error = "Missing url argument, specify as --url https://domain.com"
        return False, error, None


def testconnect(pluginargs, args, api, useragent):

    success = True
    headers = {
        'User-Agent' : useragent,
    }

    headers = utils.add_custom_headers(pluginargs, headers)

    resp = api.get("/remote/login?lang=en", headers=headers)

    if resp.status_code == 504:
        output = "Testconnect: Connection failed, endpoint timed out, exiting"
        success = False
    elif "fortinet" in resp.text:
        output = "Testconnect: Verified Fortinet instance, connected"
    else:
        output = "Testconnect: Warning, Fortinet client not indicated, continuing"

    return success, output, pluginargs
