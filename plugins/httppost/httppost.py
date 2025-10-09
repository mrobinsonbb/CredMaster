import utils.utils as utils


def httppost_authenticate(api, username, password, useragent, pluginargs):

    data_response = {
        'result' : None,    # Can be "success", "failure" or "potential"
        'error' : False,
        'output' : "",
        'valid_user' : False
    }

    # CHANGEME: Add more if necessary
    headers = {
        'User-Agent' : useragent,
    }

    # Adds content-type to headers before custom headers, so that the user can overwrite it if needed
    if pluginargs['content-type'] == "form":
        headers['Content-Type'] = "application/x-www-form-urlencoded"
    elif pluginargs['content-type'] == "json":
        headers['Content-Type'] = "application/json"

    headers = utils.add_custom_headers(pluginargs, headers)

    try:

        resp = None

        # Replace {USER} and {PASS} placeholders in the body
        body = pluginargs['body'].replace("{USER}", username).replace("{PASS}", password)

        resp = api.post(f"/{pluginargs['uri']}", data=body, headers=headers, verify=False, timeout=30)

        if resp.status_code == 200:
            data_response['result'] = "success"
            data_response['output'] = f"[+] SUCCESS: => {username}:{password}"
            data_response['valid_user'] = True

        elif resp.status_code == 401:
            data_response['result'] = "failure"
            data_response['output'] = f"[-] FAILURE: => {username}:{password}"

        else: #fail
            data_response['result'] = "potential"
            data_response['output'] = f"[?] UNKNOWN_RESPONSE_CODE: {resp.status_code} => {username}:{password}"

    except Exception as ex:
        data_response['error'] = True
        data_response['output'] = ex
        pass

    return data_response
