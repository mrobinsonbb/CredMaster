import utils.utils as utils


def adfs_authenticate(api, username, password, useragent, pluginargs):

    data_response = {
        'result' : None,    # Can be "success", "failure" or "potential"
        'error' : False,
        'output' : "",
        'valid_user' : False
    }

    # post_data = urllib.parse.urlencode({'UserName': username, 'Password': password,
    #                                    'AuthMethod': 'FormsAuthentication'}).encode('ascii')
    post_data = {
        'UserName' : username,
        'Password' : password,
        'AuthMethod' : 'FormsAuthentication'
    }

    # ?client-request-id=&wa=wsignin1.0&wtrealm=urn:federation:MicrosoftOnline&wctx=cbcxt=&username={}&mkt=&lc=
    params_data =  {
        'client-request-id' : '',
        'wa' : 'wsignin1.0',
        'wtrealm' : 'urn:federation:MicrosoftOnline',
        'wctx' : '',
        'cbcxt' : '',
        'username' : username,
        'mkt' : '',
        'lc' : '',
        'pullStatus' : 0
    }

    headers = {
        'User-Agent' : useragent,

        'Content-Type' : 'application/x-www-form-urlencoded',
        'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9, image/webp,*/*;q=0.8'
    }

    headers = utils.add_custom_headers(pluginargs, headers)

    try:

        resp = api.post("/adfs/ls/", headers=headers, params=params_data, data=post_data, allow_redirects=False)

        if resp.status_code == 302:
            data_response['result'] = "success"
            data_response['output'] = f"[+] SUCCESS: => {username}:{password}"
            data_response['valid_user'] = True

        else:  # fail
            data_response['result'] = "failure"
            data_response['output'] = f"[-] FAILURE: {resp.status_code} => {username}:{password}"

    except Exception as ex:
        data_response['error'] = True
        data_response['output'] = ex
        pass

    return data_response
