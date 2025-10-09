import utils.utils as utils


def gmailenum_authenticate(api, username, password, useragent, pluginargs):

    data_response = {
        'result' : None,    # Can be "success", "failure" or "potential"
        'error' : False,
        'output' : "",
        'valid_user' : False
    }

    headers = {
        'User-Agent' : useragent,
    }

    headers = utils.add_custom_headers(pluginargs, headers)

    try:

        resp = api.get("/mail/gxlu",params={"email":username},headers=headers)

        if "Set-Cookie" in resp.headers.keys():
            data_response['result'] = "success"
            data_response['output'] = f"[!] VALID_USERNAME: {username} - Status: {resp.status_code}"
            data_response['valid_user'] = True

        else:
            data_response['result'] = "failure"
            data_response['output'] = f"[-] UNKNOWN_USERNAME: {username} - Status: {resp.status_code}"


    except Exception as ex:
        data_response['error'] = True
        data_response['output'] = ex
        pass

    return data_response
