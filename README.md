# openqa_client

This is a client for the [openQA](https://os-autoinst.github.io/openQA/)
API, based on [requests](https://python-requests.org). It requires Python
3.6 or later.

## Usage

Here's a simple example of reading the status of a job:

    from openqa_client.client import OpenQA_Client
    client = OpenQA_Client(server='openqa.opensuse.org')
    print(client.openqa_request('GET', 'jobs/1'))

Here's an example of triggering jobs for an ISO:

    # This is a Fedora server.
    client = OpenQA_Client(server='openqa.happyassassin.net')
    params = {}
    params['ISO'] = '22_Beta_TC2_server_x86_64_boot.iso'
    params['DISTRI'] = 'fedora'
    params['VERSION'] = '22'
    params['FLAVOR'] = 'server_boot'
    params['ARCH'] = 'x86_64'
    params['BUILD'] = '22_Beta_TC2'
    print(cl.openqa_request('POST', 'isos', params))

All methods other than `GET` require authentication. This client uses
the same configuration file format as the reference (perl) client in
openQA itself. Configuration will be read from `/etc/openqa/client.conf`
or `~/.config/openqa/client.conf`. A configuration file looks like this:

    [openqa.happyassassin.net]
    key = APIKEY
    secret = APISECRET

You can get the API key and secret from the web UI after logging in. Your
configuration file may include credentials for multiple servers; each
section contains the credentials for the server named in the section
title.

If you create an `OpenQA_Client` instance without passing the `server`
argument, it will use the first server listed in the configuration file
if there is one, otherwise it will use 'localhost'. Note: this is a
difference in behaviour from the perl client, which *always* uses 'localhost'
unless a server name is passed.

TLS/SSL connections are the default (except for localhost). You can
pass the argument `scheme` to `OpenQA_Client` to force the use of
unencrypted HTTP, e.g.
`OpenQA_Client(server='openqa.happyassassin.net', scheme='http')`.

The API always returns JSON responses; this client's request functions
parse the response before returning it.

If you need for some reason to make a request which does not fall into
the `openqa_request()` method's expected pattern, you can construct a
`requests.Request` and pass it to `do_request()`, which will attach the
required headers, execute the request, and return the parsed JSON response.

The `const` module provides several constants that are shadowed from the
upstream openQA code, including job states, results, and the 'scenario
keys'.

## Licensing

This software is available under the GPL, version 2 or any later version.
A copy is included as COPYING.
