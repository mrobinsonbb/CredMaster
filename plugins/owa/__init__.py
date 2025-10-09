import utils.utils as utils


def validate(pluginargs, args):
    #
    # Plugin Args
    #
    # --url https://mail.domain.com   ->  OWA mail target
    #
    if 'url' in pluginargs.keys():
        return True, None, pluginargs
    else:
        error = "Missing url argument, specify as --url https://mail.domain.com"
        return False, error, None


def testconnect(pluginargs, args, api, useragent):

    success = True
    headers = {
        'User-Agent' : useragent,
    }

    headers = utils.add_custom_headers(pluginargs, headers)

    resp = api.get(headers=headers, verify=False)

    if resp.status_code == 504:
        output = "Testconnect: Connection failed, endpoint timed out, exiting"
        success = False
    else:
        output = "Testconnect: Fingerprinting host... Internal Domain name: {domain}, continuing"

    if success:
        domainname = utils.get_owa_domain(api, "/autodiscover/autodiscover.xml", useragent)
        output = output.format(domain=domainname)
        pluginargs['domain'] = domainname

    return success, output, pluginargs
