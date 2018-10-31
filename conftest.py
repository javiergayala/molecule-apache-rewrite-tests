"""Configure pytest.

Configuration for py.test.  Provides the ability to read tests from a YAML file.
"""
import pytest
import requests
from urllib3.exceptions import NewConnectionError, MaxRetryError
import os


def pytest_addoption(parser):
    """Add the boolean option to test against a remote server(s)."""
    parser.addoption("--use_remote", action="store", type=bool, default=False,
                     help="Run tests against remote web server")


def pytest_collect_file(parent, path):
    """Collect the test*.yml files."""
    if path.ext == ".yml" and path.basename.startswith("test"):
        return YamlFile(path, parent)


class YamlFile(pytest.File):
    """Class representing a YAML file containing redirects."""

    def collect(self):
        """Import and parse a YAML file of redirects.

        Arguments:
            pytest {obj} -- YAML file containing redirects
        """
        import yaml  # we need a yaml parser, e.g. PyYAML
        yamlData = yaml.safe_load(self.fspath.open())
        for hostname, rules in sorted(yamlData.items()):
            for rule in rules:
                if "tests" in rule:
                    for test in rule["tests"]:
                        yield YamlItem(hostname, self.parent, rule, test)
                else:
                    yield YamlItem(hostname, self.parent, rule, None)


class YamlItem(pytest.Item):
    """A single redirect rule.

    Arguments:
        pytest {dict} -- dictionary containing the test data of the redirect rule

    Raises:
        ConnectionErrorException -- Unable to connect to the web server
        GenericRequestException -- Unable to continue for an unknown reason
        StatusCodeException -- Status Code mismatch between expected and actual
        LocationMatchException -- Mismatch between expected redirect and actual

    """

    def __init__(self, hostname, parent, rule, test):
        """Initialize the data for the rule test.

        Arguments:
            hostname {str} -- Hostname to test
            parent {obj} -- parent
            rule {dict} -- dictionary containing the redirect rule
            test {dict} -- dictionary containing the data used to construct the test
        """
        super(YamlItem, self).__init__(hostname, parent)
        # self.destination = self.get_ansible_info()
        self.destination = "127.0.0.1:1975"
        self.hostname = hostname
        self.rule = rule
        self.test = test
        self.scheme = self.rule["scheme"] if "scheme" in self.rule else "https"
        self.path = self.test["request_uri"] if self.test and "request_uri" in self.test else self.rule["path"]
        self.return_code = self.test["code"] if self.test and "code" in self.test else self.rule["code"]
        self.return_url = self.test["url"] if self.test and "url" in self.test else None

    # def get_ansible_info(self):
    #     """Obtain the IP of the host we are targeting with our tests.

    #     Returns:
    #         str -- IP Address of the target host.

    #     """
    #     from testinfra.utils.ansible_runner import AnsibleRunner
    #     testinfra_hosts = AnsibleRunner(os.environ['MOLECULE_INVENTORY_FILE']).run(
    #         'gsd8-a-d2.test.rakr.net', "debug", module_args="var=destination_ip")
    #     return testinfra_hosts['destination_ip']

    def runtest(self):
        """Perform a request and compare to expected results.

        Raises:
            ConnectionErrorException -- Unable to connect to the web server
            GenericRequestException -- Unable to continue for an unknown reason
            StatusCodeException -- Status Code mismatch between expected and actual
            LocationMatchException -- Mismatch between expected redirect and actual

        """
        if self.test:
            source = ("%s://%s%s" % (self.scheme, self.destination, self.path))
            headers = {"host": self.hostname}
            if "headers" in self.test:
                headers.update(self.test["headers"])
            try:
                r = requests.get(source, headers=headers,
                                 allow_redirects=False)
            except Exception as e:
                raise ConnectionErrorException(self, "%s %s" % (
                    pytest.config.getoption('use_remote'), e))
            if not r.ok:
                if r.status_code == self.return_code and r.status_code == 404:
                    return
                else:
                    raise GenericRequestException(
                        self, self.hostname, source, r)
            if not r:
                raise GenericRequestException(
                    self, "Couldn't initiate a request. | Source: %s | Headers: %s  | Expected Return Code: %s | Expected Redirect Location: %s|" % (source, headers, self.return_code, self.return_url))
            if r.status_code != self.return_code:
                raise StatusCodeException(
                    self, self.return_code, r.status_code, source)
            if self.return_url:
                if r.headers['Location'] != self.return_url:
                    raise LocationMatchException(
                        self, self.return_url, r.headers['Location'], source)
        else:
            pytest.skip("No test associated with this rule.")

    def repr_failure(self, excinfo):
        """Call when self.runtest() raises an exception."""
        if isinstance(excinfo.value, YamlException):
            return "\n".join(
                [
                    "usecase execution failed",
                    "   expected: %r received: %r" % excinfo.value.args[1:3],
                    "   no further details known at this point.",
                ]
            )
        if isinstance(excinfo.value, StatusCodeException):
            return "\n".join(
                [
                    "usecase execution failed for Status Code",
                    "   target: %s" % excinfo.value.args[3],
                    "   expected: %r received: %r" % excinfo.value.args[1:3],
                    "   no further details known at this point.",
                ]
            )
        if isinstance(excinfo.value, LocationMatchException):
            return "\n".join(
                [
                    "usecase execution failed for Location Match",
                    "   target: %s" % excinfo.value.args[3],
                    "   expected: %r  received: %r" % excinfo.value.args[1:3],
                    "   no further details known at this point.",
                ]
            )
        if isinstance(excinfo.value, GenericRequestException):
            return "\n".join(
                [
                    "usecase execution failed due to a generic issue",
                    "   URL: %r" % excinfo.value.args[-1].request.url,
                    "   Req. headers: %r" % excinfo.value.args[-1].request.headers,
                    "   Resp. headers: %r" % excinfo.value.args[-1].headers,
                    "   status_code: %r" % excinfo.value.args[-1].status_code,
                    "   no further details known at this point.",
                ]
            )
        if isinstance(excinfo.value, ConnectionErrorException):
            return "\n".join(
                [
                    "usecase execution failed due to a Connection Error",
                    "   received: %r" % excinfo.value,
                    "   no further details known at this point.",
                ]
            )

    def reportinfo(self):
        """Information for the report header."""
        return self.fspath, 0, "usecase: %s -> %s" % (self.name, self.path)


class YamlException(Exception):
    """Custom exception for error reporting."""


class StatusCodeException(Exception):
    """Custom exception for status code mismatches."""


class LocationMatchException(Exception):
    """Custom exception for Location mismatches."""


class GenericRequestException(Exception):
    """Custom exception for Location mismatches."""


class ConnectionErrorException(Exception):
    """Custom exception for Location mismatches."""
