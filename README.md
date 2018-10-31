# molecule-apache-rewrite-tests
Adds the ability to test Apache rewrites/redirects when using Molecule.

## Requirements

- [Molecule](https://github.com/ansible/molecule)  
- [Docker](https://www.docker.com/)  

## Overview

The `conftest.py` file is used to configure `py.test` to read a YAML file containing information on how to define the tests for Apache rewrite/redirect rules.

### `conftest.py`

This is my personal `conftest.py` for this scenario, and may not suit everyone's needs.  In this particular scenario, it assumes that Molecule is using Docker as it's backend, and that Molecule is configured to publish port `80` on the Docker container to port `1975` on the Docker host.  The `conftest.py` file should be installed within your Molecule scenario directory.  For example:

`ansible-playbook-apache/molecule/default/tests/conftest.py`

### `test_redirects.yml`

This is an example of what the `test_redirects.yml` file would look like:

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
        code: 200
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
  - `code`: the status code that you expect to receive back from the web server  
  - `headers`: dictionary containing extra headers that you want to include in the request  
  
