import utils.utils as utils
import gzip
import zlib


def o365enum_authenticate(api, username, password, useragent, pluginargs):

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

        # some code stolen from:
        # https://github.com/BarrelTit0r/o365enum/blob/master/o365enum.py
        # https://github.com/dievus/Oh365UserFinder/blob/main/oh365userfinder.py

        if_exists_result_codes = {
            "-1" : "UNKNOWN_ERROR",
            "0" : "VALID_USERNAME",
            "1" : "UNKNOWN_USERNAME",
            "2" : "THROTTLE",
            "4" : "ERROR",
            "5" : "VALID_USERNAME_DIFFERENT_IDP",
            "6" : "VALID_USERNAME"
        }

        domainType = {
            "1" : "UNKNOWN",
            "2" : "COMMERCIAL",
            "3" : "MANAGED",
            "4" : "FEDERATED",
            "5" : "CLOUD_FEDERATED"
        }

        body = '{"username":"%s"}' % username

        response = api.post("/common/GetCredentialType", headers=headers, data=body)

        #print(f"{response.headers}")
        throttle_status = int(response.json()['ThrottleStatus'])
        if_exists_result = str(response.json()['IfExistsResult'])
        if_exists_result_response = if_exists_result_codes[if_exists_result]
        domain_type = domainType[str(response.json()['EstsProperties']['DomainType'])]
        domain = username.split("@")[1]

        if domain_type != "MANAGED":
            data_response["result"] = "failure"
            data_response['output'] = f"[-] FAILURE: {username} Domain type {domain_type} not supported for user enum"

        elif throttle_status != 0 or if_exists_result_response == "THROTTLE":
            data_response['output'] = f"[?] WARNING: Throttle detected on user {username}"
            data_response['result'] = "failure"
            data_response['error'] = True

        else:
            sign = "[-]"
            data_response["result"] = "failure"
            if "VALID_USER" in if_exists_result_response:
                sign = "[!]"
                data_response["result"] = "success"
                data_response['valid_user'] = True
            data_response['output'] = f"{sign} {if_exists_result_response}: {username}"

    except Exception as ex:
        data_response['error'] = True
        data_response['output'] = ex
        data_response['debug'] = response.text
        #data_response['debug1'] = ""
        #data_response['debug2'] = response.text
        #if "Content-Encoding" in response.headers:
        #    data_response['debug1'] = response.headers["Content-Encoding"]
        #    if response.headers["Content-Encoding"] == "gzip":
        #        try:
        #            t = gzip.decompress(response.text.encode("latin1"))
        #        except:
        #            t = "unable to ungzip"
        #        data_response['debug2'] = t
        pass

    return data_response
