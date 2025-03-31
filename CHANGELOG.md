## Changelog

### 4.3.0 - 2025-03-31

1.  Add new `get_latest_build` method (asmorodskyi)

### 4.2.3 - 2023-10-03

1.  Add py.typed marker to the package

### 4.2.2 - 2023-09-05

1.  Include the response text in RequestError (kalikiana)
2.  Support `REQUESTS_CA_BUNDLE` and `CURL_CA_BUNDLE` environment variables (ricardobranco777)

### 4.2.1 - 2022-11-09

1.  Make Exceptions proper objects with members (perlpunk)
2.  Only retry requests on certain status codes

### 4.2.0 - 2022-09-13

1.  Add class global retries and wait values to allow configuration (dcermak)
2.  Add type hints (dcermak)
3.  Stop encoding X-API-Microtime as bytes (dcermak)
4.  Build and CI system modernizations and improvements

### 4.1.2 - 2021-04-27

1.  Improve handling of quirky API behaviour regarding settings parameters

### 4.1.1 - 2020-08-07

1.  Fix `latest` param when querying jobs to use value `1` not `true`

### 4.1.0 - 2020-03-13

1.  Handle server sending us YAML (though we didn't ask for it)
2.  Add `parse` kwarg to `do_request` to allow skipping parsing

This adds a dependency on pyyaml, unfortunately; can't see any way around that short of
just not parsing these responses at all.

### 4.0.0 - 2020-02-28

1.  Drop Python 2 support, remove various Python 2-specific workarounds
2.  Move module source under `src/`
3.  Make tox build and test an sdist, not test the working directory
4.  Run [black](https://github.com/psf/black) on the source, add it to CI
5.  Add `pyproject.toml` compliant with PEP-517 and PEP-518
6.  Update `release.sh` to use `pep517`

This is a modernization release to drop Python 2 support and align with various shiny modern
Best Practices. There should be no actual functional changes to the code at all, but I'm gonna
call it 4.0.0 due to the dropping of Python 2 support and the code being moved within the
git repo, which may disrupt some folks.

### 3.0.4 - 2020-02-27

1.  OK, this time fix tests on ancient EPEL 7 for realz
2.  Tweak py27 tox environment to match EPEL 7

### 3.0.3 - 2020-02-27

1.  Fix tests to run on ancient pytest in EPEL 7 (I hope)

### 3.0.2 - 2020-02-27

1.  Fix more broken stuff in setup.py

### 3.0.1 - 2020-02-27

1.  Drop duplicated description line in setup.py
2.  Fix release.sh for no spaces in setup.py setup()

### 3.0.0 - 2020-02-27

1.  **API**: remove `WaitError` exception
2.  Update release script to use Python 3, publish to PyPI
3.  Update setup.py for current best practices
4.  Don't modify original request in `_add_auth_headers`
5.  Don't edit list while iterating it in `find_clones`
6.  Add a test suite, tox config and GitHub Actions-based CI

### 2.0.1 - 2020-02-26

1.  Fix long description for PyPI

### 2.0.0 - 2020-01-06

1.  Update constants to reflect upstream changes again, including
    some additions and **REMOVAL** of JOB_INCOMPLETE_RESULTS

### 1.3.2 - 2019-05-21

1.  Update constants to reflect upstream changes (again)

### 1.3.1 - 2017-10-10

1.  Update constants to reflect upstream changes

### 1.3.0 - 2017-02-15

1.  First proper release
