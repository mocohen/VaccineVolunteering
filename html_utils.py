import requests
from datetime import datetime, timedelta, timezone, date
import re
import gc_storage_utils
import pytz
import pandas as pd

from scrapy.http import TextResponse, HtmlResponse


def get_url(url, client):
    '''Generate proxy scraper api url

    Args:
        url (string): url 
        client (ScraperAPIClient): scraper api client
    Returns:
        proxy_url (string): proxy url
    '''

    return client.scrapyGet(url = url, country_code = "US")


def request_page(url, client):
    '''retrieve html text response from url

    Args:
        url (string): url 
        client (ScraperAPIClient): scraper api client
    Returns:
        resp (TextResponse): html text response
    '''

    req = requests.get(get_url(url, client))
    resp = TextResponse(req.url, body=req.text, encoding='utf-8')
    return resp

def get_new_rows(response):
    '''search and find new rows in POST response

    Args:
        response (Response): POST response 
    Returns:
        text (string): string with new rows
    '''

    #find beginning of new rows string
    beg_regex = re.compile('\|\d+\|updatePanel\|ContentPlaceHolder1_UpdatePanelSchedule\|')
    start_ind = beg_regex.search(response.text).end()

    # find next update panel after start_ind
    for m in re.finditer('\|\d+\|updatePanel\|', response.text):
        if m.start() > start_ind:
            return response.text[start_ind: m.start()]

def get_event_viewstate(response):
    viewstate_dict = {}
    # event_validation = ''
    # view_state = ''
    splits = response.text.split('|')
    for v, vals in enumerate(splits):
        if vals == '__EVENTVALIDATION':
            viewstate_dict["event_validation"] = splits[v+1]
        elif vals == '__VIEWSTATE':
            viewstate_dict["view_state"] = splits[v+1]
        elif vals == '__VIEWSTATEGENERATOR':
            viewstate_dict['generator'] = splits[v+1]


    assert len(viewstate_dict) > 0, "no view state or event val returned" + response.text
    return viewstate_dict

def make_request(param_dict):
    data_dict = {
        'view_state': '',
        'event_validation': '',
        'profession':'',
        'profession_ID': '-1',
        'row_id': '',
        'state_id': '',
    }
    if not 'hidden_field' in param_dict:
        param_dict['hidden_field'] = param_dict['profession']

    for key, val in param_dict.items():
        data_dict[key] = val
    return request_date_template(data_dict)


def str_to_datetime(date_str):
    # print(date_str)
    return datetime.strptime(date_str, '%a %b %d').date()

def date_to_bigquery(date):
    return date.strftime('%Y-%m-%d')

def timestamp_to_bigquery(date):
    return date.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f %Z')

def check_date(row_id, date_range_text, top_response, old_events = [], profession='G'):
    '''Check date range for new events

    Args:
        row_id (string): number id of date range as a string
        date_range_text (string): date range as text
        top_response (Response): html response of main page
    Returns:
        events (string): string with available events
    '''
    print(profession)
    view_state = top_response.xpath('//div[@class="aspNetHidden"]/input[@name="__VIEWSTATE"]/@value').get()
    event_validation = top_response.xpath('//div[@class="aspNetHidden"]/input[@name="__EVENTVALIDATION"]/@value').get()

    if profession == 'MP':
        prof = 'M'
        prof_id = '16'
        license_req = '1'


        data0 = {
            'view_state':view_state, 
            'event_validation':event_validation,
            'generator':'CA0B0334',
            'profession':prof,
            'license_req': '0',
            'hidden_field': 'G',
        }            
        zero_response = make_request(data0)
        ev0 = get_event_viewstate(zero_response)

        view_state = ev0['view_state']
        event_validation = ev0['event_validation']


    elif profession == 'G-CP2':
        prof='G'
        prof_id = '175'
        license_req = '0'

    elif profession == 'G':
        prof_id = '68'
        prof='G'
        license_req = '0'

    # choose general
    data1 = {
            'view_state':view_state, 
            'event_validation':event_validation,
            'generator':'CA0B0334',
            'profession':prof,
            'profession_ID': prof_id,
            'license_req':license_req
}
    
    first_response = make_request(data1)
    # print( first_response.text)
    ev1 = get_event_viewstate(first_response)
    
    # choose second general
    data2 = {
            'view_state':ev1['view_state'], 
            'event_validation':ev1['event_validation'],
            'generator': ev1['generator'],
            'profession':prof,
            'profession_ID': prof_id,
            'license_req':license_req,
            'state_id':'47'
    }
    second_response = make_request(data2)
    # print('\n\n\nsecond',second_response.text)
    # print(f'\n\n\nrow id :{row_id}')

    ev2 = get_event_viewstate(second_response)

    # request specific date range
    data3 = {
            'view_state':ev2['view_state'], 
            'event_validation':ev2['event_validation'],
            'generator': ev2['generator'],
            'profession':prof,
            'profession_ID': prof_id,
            'license_req':license_req,
            'state_id':'47',
            'row_id': row_id,
    }
    third_response = make_request(data3)
    # print('\n\n\nthird',third_response.text)

    html_text_string = get_new_rows(third_response)
    new_text_response = HtmlResponse(url="my HTML string", body=html_text_string, encoding='utf-8')


    # add timezone
    offset = timezone(timedelta(hours=-8))
    now = datetime.now(offset)

    events = []
    full_events = []
    sent_events = []
    new_events = []
    for tr in new_text_response.xpath('//tr'):
        date_str = tr.xpath('./td/text()').get().strip()


        if len(tr.xpath('td/div/select')) > 0:
            date = str_to_datetime(date_str).replace(year=now.year)

            if (date not in old_events.index.values):
                new_events.append({u"date":date_to_bigquery(date), 
                    u"last_accessed":timestamp_to_bigquery(datetime.now()),
                    u"profession":profession})
                events.append(date_str)
            else:
                sent_events.append(date_str)    
        else:
            full_events.append(date_str)


    
    print('full', full_events)
    print('old', sent_events)
    print('events', events)


    if len(new_events) > 0:
        gc_storage_utils.upload_new_dates(new_events)

    if len(events) > 0:
        # if len(events) > 1:
            return ", ".join(events)   
        # else:
            # offset = timezone(timedelta(hours=-8))
            # now = datetime.now(offset)
            # date = datetime.strptime(events[0], '%a %b %d').replace(year=now.year, tzinfo=offset)
            # if timedelta(days=.75) < (date - now):
                # return events[0]
    return

def request_date_template(data_dict):
    '''Generate POST request for changing row

    Args:
        row_id (string): number id of date range as a string
        view_state (string): view state string from main page response
        event_validation (string): event validation string from main page response
    Returns:
        response (Response): POST response for changing dates
    '''
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:85.0) Gecko/20100101 Firefox/85.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'X-Requested-With': 'XMLHttpRequest',
        'X-MicrosoftAjax': 'Delta=true',
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        'Origin': 'https://communityvaccination.org',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Referer': 'https://communityvaccination.org',
    }

    data = {
      'ctl00$ContentPlaceHolder1$ScriptManager1': 'ctl00$ContentPlaceHolder1$UpdatePanelOpKey|ctl00$ContentPlaceHolder1$DropDownListOpKey',
      '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$DropDownListOpKey',
      '__EVENTARGUMENT': '',
      '__LASTFOCUS': '',
      '__VIEWSTATE': f'{data_dict["view_state"]}',
      '__VIEWSTATEGENERATOR': data_dict['generator'],
      '__VIEWSTATEENCRYPTED': '',
      '__EVENTVALIDATION': f'{data_dict["event_validation"]}',
      # 'ctl00$ContentPlaceHolder1$TextBoxTitle': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxFirstName': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxLastName': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxProfAbbre': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxBadge': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxPhone': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxPhoneConfirm': '',
      'ctl00$ContentPlaceHolder1$DropDownListPhoneType': '-1',
      # 'ctl00$ContentPlaceHolder1$TextBoxAddr1': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxAddr2': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxCity': '',
      'ctl00$ContentPlaceHolder1$DropDownListState': '-1',
      # 'ctl00$ContentPlaceHolder1$TextBoxZip': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxEmail': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxEmail2': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxUserName': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxPassword': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxPasswordVerify': '',
      'ctl00$ContentPlaceHolder1$DropDownTShirt': '-1',
      'ctl00$ContentPlaceHolder1$ListBoxLanguages': '-1',
      # 'ctl00$ContentPlaceHolder1$TextBoxCompanyName': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxEmployersPlan': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxEmergencyName': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxEmergencyRelationship': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxEmergencyPhone': '',
      'ctl00$ContentPlaceHolder1$RepeaterAttributes$ctl01$HiddenField1':'38',
      'ctl00$ContentPlaceHolder1$RepeaterAttributes$ctl02$HiddenField1':'39',
      'ctl00$ContentPlaceHolder1$RepeaterAttributes$ctl03$HiddenField1':'40',
      'ctl00$ContentPlaceHolder1$DropDownListAreas': f'{data_dict["profession"]}',
      'ctl00$ContentPlaceHolder1$HiddenFieldArea': f'{data_dict["hidden_field"]}',
      'ctl00$ContentPlaceHolder1$DropDownListProfessions': f'{data_dict["profession_ID"]}',
      'ctl00$ContentPlaceHolder1$HiddenFieldProfessionLicenseReq': data_dict['license_req'],
      'ctl00$ContentPlaceHolder1$HiddenFieldInsuranceReq':  data_dict['license_req'],
      'ctl00$ContentPlaceHolder1$HiddenFieldIsStudentProfession': '0',
      # 'ctl00$ContentPlaceHolder1$TextBoxComments': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxLicense': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxLicenseDate': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxLiabilityInsurance': '',
      'ctl00$ContentPlaceHolder1$DropDownListStateLicense': '-1',
      # 'ctl00$ContentPlaceHolder1$TextBoxLicenseComment': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxResLocation': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxResSupervisor': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxSchool': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxStudentFieldOfStudy': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxStudentYearOfStudy': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxFaculty': '',
      'ctl00$ContentPlaceHolder1$DropDownListStateLimit': f'{data_dict["state_id"]}',
      'ctl00$ContentPlaceHolder1$DropDownListOpKey': f'{data_dict["row_id"]}',
      # 'ctl00$ContentPlaceHolder1$TextBoxAdminCode': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxDocName1': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxDocName2': '',
      # 'ctl00$ContentPlaceHolder1$TextBoxDocName3': '',
      # 'ContentPlaceHolder1_ctlSignature_data': '',
      # 'ContentPlaceHolder1_ctlSignature_data_smooth': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldVolKey': '0',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldOpAssignDayKeyList': '',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldAlternateOpAssignDayKeyList': '',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldDisplayedQuestionList': '',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldDisplayedAnswerList': '',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldWaitListed': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldSignatureFile': 'none',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldYesValues': '',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldNoValues': '',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldDropDownValues': '',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldTextBoxValues': '',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldCommentList': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldAdminKey': '0',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldInitialComments': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldCommentsAllowed': 'False',
      'ctl00$ContentPlaceHolder1$HiddenFieldDropDownQKey': '0',
      'ctl00$ContentPlaceHolder1$HiddenFieldShowFaculty': 'False',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldOriginalFirstName': '',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldOriginalLastName': '',
      # 'ctl00$ContentPlaceHolder1$HiddenFieldErrorClientIDArray': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldDesktop': 'True',
      'ctl00$ContentPlaceHolder1$HiddenFieldShowMatching': 'False',
      'ctl00$ContentPlaceHolder1$HiddenFieldProfileAllowed': 'False',
      'ctl00$ContentPlaceHolder1$HiddenFieldAllowVolunteerDocuments': 'False',
      'ctl00$ContentPlaceHolder1$HiddenFieldVolDocKey': '0',
      'ctl00$ContentPlaceHolder1$HiddenFieldSignatureImageS3': '0',
      'ctl00$ContentPlaceHolder1$HiddenFieldSecretKey': '0',
      'scrollY': '2646',
      '__ASYNCPOST': 'true',
      '': ''
    }

    response = requests.post('https://communityvaccination.org', headers=headers, data=data)
    return response