"""
Shoutbase API client for python3

Usage:
    >>> from shoutbase import ShoutbaseReport
    >>> user_params = {'username': 'me', 'password': '123'}
    >>> report = ShoutbaseReport(user_params)
    >>> report.run(report_params)

"""
import time
from io import StringIO
import requests

import pandas as pd

try:
    from urllib.parse import quote_plus  # for Python 2.x
except ImportError:
    from urllib import quote_plus  # for Python 3.x

class ShoutbaseClient(object):
    """
    Base Helper class for the ShoutBase API
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
        self.report_data = None

    def run(self, report_params=None):
        """
        Run the report:
            1) Get report URL if needed
            2) Fetch data using API
            3) TODO: create report
        """
        if report_params is not None:
            self.compose_report_url(report_params)
        if self.report_url is None:
            return Exception("Report not defined.")

        response = requests.get(self.report_url,
                                auth=(self.username, self.password))

        self.report_data = response.text
        report_df = self.format_report()
        return report_df

    def format_report(self,
                      pythonic_colnames=True,
                      short_usernames=True,
                      ):
        """
        Format report:
            * Convert raw report data to a dataframe
            * Apply transformations applicable to all reports

        """
        if not self.report_data:
            raise Exception("Report has not yet been run.")

        report_df = pd.read_csv(StringIO(self.report_data))

        # deal with datetime format
        tsformat = '%Y-%m-%d %H:%M:%S +%f UTC'
        time_cols = ['startAt', 'endAt']
        report_df[time_cols] = report_df[time_cols]\
                  .apply(pd.to_datetime, format=tsformat)

        # truncate usernames
        trunc_name = lambda x: x.split('@')[0]
        if short_usernames:
            report_df.creator = report_df.creator.apply(trunc_name)

        # renaming columns
        rename_map = {
            'startAt': 'start_time',
            'endAt': 'end_time',
            'durationHours': 'duration_hours',
            'tagNames': 'tags',
            'teamNames': 'teams',
            'description': 'description',
            'creator': 'person',
        }
        if pythonic_colnames:
            report_df = report_df.rename(index=str, columns=rename_map)

        return report_df

    def compose_report_url(self, report_params):
        """Define report parameters, do not run report
        """
        # TODO: run some checks on input
        team_name = report_params['team_name']
        start_date = report_params['start_date']
        end_date = report_params['end_date']
        tag_list = report_params.get('tag_list', [])
        tag_filter_type = report_params.get('tag_filter_type', None)

        # conversions
        tag_ids = list(map(self._tagid_from_name, tag_list))
        team_id = self._teamid_from_name(team_name)

        # Construct report request url
        url = "".join([
            self.hostname,
            '/v1/export/timerecords?teamId=', team_id,
            '&closedOnly=false&startsBy=', self.to_epoch(start_date),
            '&endsBy=', self.to_epoch(end_date),
            '&tagIds=', ",".join(tag_ids),
            '&tagFilterType=', tag_filter_type,
        ])

        # save URL
        self.report_url = url
        return url

    """Util Methods
    """
    def _tagid_from_name(self, tag_name):
        """return tag id given tag name
        """
        url = self.hostname + '/v1/tags?name=' + quote_plus(tag_name)

        # fetch data
        resp = requests.get(url, auth=(self.username, self.password))
        data = resp.json()["data"]

        # get tag id
        tag_id = data[0]["id"] if data else ""
        return tag_id

    def _teamid_from_name(self, name):
        """return team id given team name
        """
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
    def to_epoch(date):
        """date format conversion
        """
        pattern = '%Y-%m-%d'
        epoch = int(time.mktime(time.strptime(date, pattern)))
        return str(epoch * 1000)


class ShoutbaseReport(ShoutbaseClient):
    """Extends base client with standard reports
    """

    def total_hours_by_user(self, report_params):
        """Total hours reported per user"""
        raw_df = self.run(report_params=report_params)

        report_df = raw_df.pivot_table(
            values='duration_hours', aggfunc='sum',
            index='person')
        return report_df

    def summary_by_week(self, report_params):
        """For each week, summarize hours reported per user"""
        raw_df = self.run(report_params=report_params)

        # create time series
        raw_ts = raw_df.set_index('start_time')

        # resample to business week starting Mondays
        report_ts = raw_ts.resample('W-MON', ).sum()
        report_ts.index.name = 'week_starting_date'

        return report_ts

    def last_report_date(self, report_params):
        """For each user, provide the last date hours were reported"""
        pass

    def hours_by_project(self, report_params):
        """Summarize the hours spent on each project"""
        report_df = self.hours_by_team(report_params)

        # rename team --> project
        report_df.index.name = 'project'
        return report_df

    def hours_by_team(self, report_params):
        """Summarize the hours spent by each team"""
        raw_df = self.run(report_params=report_params)
        report_df = raw_df.pivot_table(
            values='duration_hours', aggfunc='sum',
            index='teams'
        )
        return report_df
