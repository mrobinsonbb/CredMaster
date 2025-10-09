from requests_ntlm import HttpNtlmAuth
import utils.utils as utils


def owa_authenticate(api, username, password, useragent, pluginargs):

    data_response = {
        'result' : None,    # Can be "success", "failure" or "potential"
        'error': False,
        'output' : "",
        'valid_user' : False
    }

    headers = {
        'User-Agent' : useragent,
        "Content-Type" : "text/xml"
    }

    headers = utils.add_custom_headers(pluginargs, headers)

    try:

        resp = api.get("/autodiscover/autodiscover.xml", headers=headers, auth=HttpNtlmAuth(username, password), verify=False)

        if resp.status_code == 200:
            data_response['output'] = f"[+] SUCCESS: Found credentials: {username}:{password}"
            data_response['result'] = "success"
            data_response['valid_user'] = True

        elif resp.status_code == 500:
            data_response['output'] = f"[*] POTENTIAL: Found credentials, but server returned 500: {username}:{password}"
            data_response['result'] = "potential"
            data_response['valid_user'] = True

        elif resp.status_code == 504:
            data_response['output'] = f"[*] POTENTIAL: Found credentials, but server returned 504: {username}:{password}"
            data_response['result'] = "potential"
            data_response['valid_user'] = True

        else:
            data_response['output'] = f"[-] FAILURE: Invalid credentials: {username}:{password}"
            data_response['result'] = "failure"


    except Exception as ex:
        data_response['error'] = True
        data_response['output'] = ex
        pass

    return data_response
