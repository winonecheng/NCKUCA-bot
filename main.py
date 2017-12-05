import requests
import json
import re
import datetime
import logging
from logging import Formatter
from logging.handlers import RotatingFileHandler
from difflib import get_close_matches

from flask import Flask, request, jsonify

DEMERIT_POINTS_SHEETS_ID = '1j44T9IkLB17Ttw3X1tgd2ua4UGvyAHU65362RjSzj_w'
CLOSED_TIME_SHEETS_ID = '18C83ua-m67ZFB3j283Ku_b5IomjyWG6xYMAEDPXZJrw'
GOOGLE_SHEETS_API = ('https://sheets.googleapis.com/v4/spreadsheets/'
                     '{sheets_id}/values/{range}?key={key}')

app = Flask(__name__)
app.config.from_envvar('YOURAPPLICATION_SETTINGS')
app.logger.setLevel(logging.INFO)
handler = logging.handlers.RotatingFileHandler(
    filename=app.config['LOG_FILENAME'],
    maxBytes=1024 * 1024 * 100,
    backupCount=10
)
handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s'
    '[in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(handler)


@app.before_request
def log_request_info():
    app.logger.info(
        ('Headers: %s'
         'Url: %s\n'
         'Method: %s\n'
         'Body: %s\n'),
        request.headers, request.url, request.method, request.get_data()
    )


@app.route('/')
def hello():
    return 'Hello World!'


@app.route('/lookup/demerit_points', methods=['GET'])
def lookup_demerit_points():
    target_club = (request.args.get('club_name') or
                   request.args.get('lookup_club_name'))
    sheet_data = requests.get(GOOGLE_SHEETS_API.format(
        sheets_id=DEMERIT_POINTS_SHEETS_ID,
        range='A1:ZZ',
        key=app.config['GOOGLE_API_KEY']
    )).json()

    close_club_name = get_close_matches(
        target_club, [row[0] for row in sheet_data['values']],
        n=1, cutoff=0.6)

    text = ''
    if close_club_name == []:
        text = '此社團違規為0點，或輸入之社團名稱錯誤，請輸入完整名稱再試'
    else:
        close_club_name = close_club_name[0]
        text = '以下為「{}」的違規記點\n\n'.format(close_club_name)

        close_club_row = next(
            row for row in sheet_data['values'] if row[0] == close_club_name)

        for idx, point in enumerate(close_club_row[1:]):
            if point:
                text += '{time}: {point}\n'.format(
                    time=sheet_data['values'][0][idx+1],
                    point=point
                )

    return jsonify({'messages': [{'text': text}]})


@app.route('/lookup/closed_time', methods=['GET'])
def lookup_closed_time():
    day_interval = request.args.get('day_interval')
    year_and_month = request.args.get('year_and_month')
    sheet_data = requests.get(GOOGLE_SHEETS_API.format(
        sheets_id=CLOSED_TIME_SHEETS_ID,
        range='A1:ZZ',
        key=app.config['GOOGLE_API_KEY']
    )).json()

    date_interval = formatted_date_interval(year_and_month, day_interval)
    target_rows = find_target_date(sheet_data, date_interval)

    text = year_and_month + '/' + day_interval + ' 的一活閉館時間：\n\n'
    if target_rows:
        for row in target_rows:
            text += '{date}\n一活閉館時間：{time}\n負責閉館社團：{clubs}\n'.format(
                date=row[0],
                time=row[1],
                clubs=', '.join(row[2:])
            )
            text += '---\n'
        text += '未列出的日期，目前皆為無延長(正常閉館時間)'
    else:
        text = "在這區間的日期，目前皆為無延長(正常閉館時間)"

    return jsonify({'messages': [{'text': text}]})


# Format yyyy/mm/dd as [y, m, d]
def formatted_date(date):
    result = re.match(r'(\d+)/(\d+)/(\d+)', date)
    if result:
        year = int(result.group(1))
        month = int(result.group(2))
        day = int(result.group(3))
        return [year, month, day]
    else:
        app.logger.error('Formatted date fail!')
        return False


# Format yyyy/mm/dd-dd as [y, m, [d, d]]
def formatted_date_interval(year_and_month, day_interval):
    result = re.match(r'(\d+)/(\d+)', year_and_month)
    result_day = re.match(r'(\d+)-(\d+)', day_interval)
    if result and result_day:
        year = int(result.group(1))
        month = int(result.group(2))
        day = list()
        day.append(int(result_day.group(1)))
        day.append(int(result_day.group(2)))
        return [year, month, day]
    else:
        app.logger.error('Formatted date interval fail!')
        return False


def find_target_date(sheet_data, interval):
    pre_idx = post_idx = None

    for idx, item in enumerate(sheet_data['values'][1:]):
        date = formatted_date(item[0])

        if (pre_idx is None and date[0] == interval[0] and
                date[1] == interval[1] and date[2] >= interval[2][0]):
            pre_idx = idx

        if (pre_idx and
            (date[2] > interval[2][1] or
             date[0] != interval[0] or
             date[1] != interval[1])):
            post_idx = idx
            break

    if pre_idx:
        if post_idx:
            return sheet_data['values'][pre_idx+1:post_idx+1]
        else:
            return sheet_data['values'][pre_idx+1:]
    else:
        return False


if __name__ == '__main__':
    app.run()
