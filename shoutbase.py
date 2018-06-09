"""
Shoutbase API client for python3

Usage:
    >>> from shoutbase import ShoutbaseReport
    >>> user_params = {'username': 'me', 'password': '123'}
    >>> report = ShoutbaseReport(user_params)
    >>> report.run(report_params)

"""
# import requests
# import urllib
# import csv
#
# try:
#     from StringIO import StringIO  # for Python 2.x
# except ImportError:
#     from io import StringIO  # for Python 3.x
#
import time
import requests

try:
    from urllib.parse import quote_plus  # for Python 2.x
except ImportError:
    from urllib import quote_plus  # for Python 3.x


class ShoutbaseReport(object):
    """
    Helper Class to create a Shoutbase report via
    API request.
    """
    def __init__(self, user_params=None):
        """
        """
        if user_params is None:
            raise Exception("user params dict not specified.")

        # API params
        self.hostname = 'https://api.shoutbase.com'
        # user params
        self.username = user_params['username']
        self.password = user_params['password']
        self.report_url = None

    def run(self, report_params=None):
        """
        Run the report:
        1) define report if not already defined
        2) fetch data using API
        3) other stuff
        """
        if report_params is not None:
            self.create_report_url(report_params)
        if self.report_url is None:
            return Exception("Report not defined.")

        response = requests.get(self.report_url,
                                auth=(self.username, self.password))

        return response
        #return True

    def create_report_url(self, report_params):
        """Define report parameters, do not run report"""

        # TODO: run some checks before saving
        team_name = report_params['team_name']
        start_date = report_params['start_date']
        end_date = report_params['end_date']
        tag_list = report_params.get('tag_list', [])
        tag_filter_type = report_params.get('tag_filter_type', None)

        # conversions
        tag_ids = self.toCommas(self.toTagIds(tag_list))
        team_id = self.toTeamId(team_name)

        # Construct report request url
        url = "".join([
            self.hostname,
            '/v1/export/timerecords?teamId=', team_id,
            '&closedOnly=false&startsBy=', self.toEpoch(start_date),
            '&endsBy=', self.toEpoch(end_date),
            '&tagIds=', tag_ids,
            '&tagFilterType=', tag_filter_type,
        ])

        # save URL
        self.report_url = url
        return True

    """Util Methods
    """

    def toTagId(self, tagName):
        tag_url = self.hostname + '/v1/tags?name=' + quote_plus(tagName)
        tag_response = requests.get(tag_url,
                                    auth=(self.username, self.password))
        tag_json = tag_response.json()
        if tag_json["data"]:
            tag_id = tag_json["data"][0]["id"]
        else:
            tag_id = ""

        return tag_id

    def toTeamId(self, name):
        team_url = self.hostname + '/v1/teams?name=' + quote_plus(name)
        team_response = requests.get(team_url,
                                     auth=(self.username, self.password))
        team_json = team_response.json()
        if team_json["data"]:
            team_id = team_json["data"][0]["id"]
        else:
            team_id = ""
        return team_id

    @staticmethod
    def toEpoch(date):
        pattern = '%Y-%m-%d'
        epoch = int(time.mktime(time.strptime(date, pattern)))
        return str(epoch * 1000)

    @staticmethod
    def toTagIds(tagNames):
        ids = list(map(lambda x: self.toTagId(x), tagNames))
        return filter(lambda x: x != "", ids)

    @staticmethod
    def toCommas(ids):
        return ",".join(ids)
