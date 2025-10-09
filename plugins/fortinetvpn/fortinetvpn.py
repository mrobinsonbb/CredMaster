import utils.utils as utils


def fortinetvpn_authenticate(api, username, password, useragent, pluginargs):

    data_response = {
        'result' : None,    # Can be "success", "failure" or "potential"
        'error' : False,
        'output' : "",
        'valid_user' : False
    }

    # CHANGEME: Add more if necessary
    headers = {
        'User-Agent' : useragent,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    headers = utils.add_custom_headers(pluginargs, headers)

    post_params = {
        "ajax" : '1',
        'username' : username,
        'credential' : password,
        'realm' : ''
    }

    if 'domain' in pluginargs.keys():
        post_params['realm'] = pluginargs['domain']

    try:

        resp = api.post("/remote/logincheck", data=post_params, headers=headers)

        if resp.status_code == 200 and 'redir=' in resp.text and '&portal=' in resp.text:
            data_response['result'] = "success"
            data_response['output'] = '[+] SUCCESS: => {}:{}'.format(username, password)
            data_response['valid_user'] = True

            if 'domain' in pluginargs.keys():
                data_response['output'] = data_response['output'] + " Domain: {}".format(pluginargs['domain'])

        else: #fail
            data_response['result'] = "failure"
            data_response['output'] = '[-] FAILURE: {} => {}:{}'.format(resp.status_code, username, password)


    except Exception as ex:
        data_response['error'] = True
        data_response['output'] = ex
        pass

    return data_response
