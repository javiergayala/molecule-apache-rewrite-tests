# molecule-apache-rewrite-tests
Adds the ability to test Apache rewrites/redirects when using pytest via Molecule.

## Requirements

- [Molecule](https://github.com/ansible/molecule)  
- [Docker](https://www.docker.com/)  
- [Pytest](https://pytest.org/)  

## Overview

The `conftest.py` file is used to configure [`py.test`](https://pytest.org/) to read a YAML file containing information detailing how to define the tests for Apache rewrite/redirect rules.

### `conftest.py`

This is my personal `conftest.py` for this scenario, and may not suit everyone's needs.  In this particular scenario, it assumes that Molecule is using Docker as it's backend, and that Molecule is configured to publish port `80` on the Docker container to port `1975` on the Docker host.  The `conftest.py` file should be installed in the same directory where your YAML file lives.  For example, since my YAML file data is also used as a variable to build out the rewrite rules via Jinja2, I have it installed here:

`ansible-playbook-apache/vars/conftest.py`

### `test_redirects.yml`/`apache_redirects.yml`

#### Molecule Setup

##### Step 1 _(May be optional)_

In my setup, this file is "truly" located under my `vars/` subdirectory and I have it named `apache_redirects.yaml`.  In order for Molecule to properly use it, you have to symlink it to your Molecule scenario's `tests` directory __AND__ it must have `test_` in the beginning of the files name.  In my case I have symlinked `vars/apache_redirects.yml` -> `molecule/default/tests/test_redirects.yml`.

##### Step 2

You need to configure your scenario's `molecule.yml` file use the additional test YAML file by including the following under the `verifier` key:

```yaml
verifier:
  name: testinfra
  additional_files_or_dirs:
     - ../../../vars/apache_redirects.yml
```

#### Apache Setup

In order to "mock" responses for files that don't exist yet on the server, you need to setup a catch-all to return `200` responses for requests that should be successfully returned.

##### `mock.html`

Add the `mock.html` file from the repo to your Apache DocumentRoot

##### VHost Conf

I have my Molecule instances in a group named `test` to differentiate them from Production or Staging.  I therefore added the following lines __to the end__ of my VHost configuration file Jinja template so that the mock response is ONLY ever added to the Apache configuration of my Molecule test instances.:

```
{% if 'test' in group_names %}
  AliasMatch ^/(?!mock.html)(.+)$ /var/www/html/mock.html
{% endif %}
```

#### YAML File
This is an example of what the `apache_redirects.yml` file would look like:

```yaml
www.site.com:
  - path: /oldpage.html
    admin_bypass: true
    scheme: http
    code: 301
    tests:
      - url: http://www.site.com/newpage.html
        code: 301
      - url: http://www.site.com/oldpage.html
        headers:
          X-Forwarded-For: 192.168.0.23
old.site.com:
  - path: '^(.*)$'
    scheme: http
    dest: http://new.site.com%{REQUEST_URI}
    code: 301
    tests:
      - request_uri: /where-are-my-pants.html
        url: http://new.site.com/where-are-my-pants.html
        code: 301
```

#### Yaml Schema

- `path`: the path that you want to match on the rewrite rule  
- `admin_bypass`: if you set this to true, then only apply the rewrite rule if the user is NOT within an "admin" IP range  
- `scheme`: whether to use `http` or `https` for the test  
- `code`: the redirect code that should be used (defaults to `301`)  
- `tests`: list of dictionaries containing the information used to create the tests  
  - `request_uri`: the uri to request from the web server  
  - `url`: the url that you expect to receive back from the web server  
  - `code`: the status code that you expect to receive back from the web server _(If you are expecting a_ `200`_ response code back, do NOT include this key.)_  
  - `headers`: dictionary containing extra headers that you want to include in the request  
  
## Authors

- __Javier Ayala__ - _Initial Work_  
