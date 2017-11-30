from flask import Flask, request, jsonify
import requests
import json
import re

from local import GOOGLE_API_KEY

FAUL_POINTS_SHEETS_ID = '1j44T9IkLB17Ttw3X1tgd2ua4UGvyAHU65362RjSzj_w'
CLOSED_TIME_SHEETS_ID = '18C83ua-m67ZFB3j283Ku_b5IomjyWG6xYMAEDPXZJrw'
GOOGLE_SHEETS_API = ('https://sheets.googleapis.com/v4/spreadsheets/'
                     '{sheets_id}/values/{range}?key={key}')

app = Flask(__name__)


@app.route('/')
def hello():
    return 'Hello World!'


@app.route('/lookup/faul_points', methods=['GET'])
def lookup_faul_points():
    sheet_data = requests.get(GOOGLE_SHEETS_API.format(
        sheets_id=FAUL_POINTS_SHEETS_ID,
        range='A1:ZZ',
        key=GOOGLE_API_KEY
    ))
    print(sheet_data.json())
    return 'yo'


@app.route('/lookup/closed_time', methods=['GET'])
def lookup_closed_time():
    day_interval = request.args.get('day_interval')
    year_and_month = request.args.get('year_and_month')
    sheet_data = requests.get(GOOGLE_SHEETS_API.format(
        sheets_id=CLOSED_TIME_SHEETS_ID,
        range='A1:ZZ',
        key=GOOGLE_API_KEY
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

    response = jsonify({'messages': [{'text': text}]})
    return response


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

        if pre_idx and date[2] > interval[2][1]:
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
