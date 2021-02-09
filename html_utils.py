import requests
from datetime import datetime, timedelta
import re

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
    event_validation = ''
    view_state = ''
    splits = response.text.split('|')
    for v, vals in enumerate(splits):
        if vals == '__EVENTVALIDATION':
            event_validation = splits[v+1]
        elif vals == '__VIEWSTATE':
            view_state = splits[v+1]
    assert len(view_state)+len(event_validation) > 0, "no view state or event val returned"
    return event_validation, view_state

def make_request(param_dict):
    data_dict = {
        'view_state': '',
        'event_validation': '',
        'profession':'',
        'profession_ID': '-1',
        'row_id': '',
    }
    for key, val in param_dict.items():
        data_dict[key] = val
    return request_date_template(data_dict)

def check_date(row_id, date_range_text, top_response, medical=False):
    '''Check date range for new events

    Args:
        row_id (string): number id of date range as a string
        date_range_text (string): date range as text
        top_response (Response): html response of main page
    Returns:
        events (string): string with available events
    '''

    view_state = top_response.xpath('//div[@class="aspNetHidden"]/input[@name="__VIEWSTATE"]/@value').get()
    event_validation = top_response.xpath('//div[@class="aspNetHidden"]/input[@name="__EVENTVALIDATION"]/@value').get()

    if medical:
        prof = 'M'
        prof_id = '63'
    else:
        prof='G'
        prof_id = '68'
    # choose general
    data1 = {
            'view_state':view_state, 
            'event_validation':event_validation,
            'profession':prof}
    
    first_response = make_request(data1)
    ev1, vs1 = get_event_viewstate(first_response)
    
    # choose second general
    data2 = {
            'view_state':vs1, 
            'event_validation':ev1,
            'profession':prof,
            'profession_ID': prof_id
    }
    second_response = make_request(data2)
    ev2, vs2 = get_event_viewstate(second_response)

    # request specific date range
    data3 = {
            'view_state':vs2, 
            'event_validation':ev2,
            'profession':prof,
            'profession_ID': prof_id,
            'row_id': row_id,
    }
    third_response = request_date_template(data3)
    
    html_text_string = get_new_rows(third_response)
    new_text_response = HtmlResponse(url="my HTML string", body=html_text_string, encoding='utf-8')
    
    events = []
    full_events = []
    for tr in new_text_response.xpath('//tr'):
        if len(tr.xpath('td/div/select')) > 0:
            events.append(tr.xpath('./td/text()').get().strip())    
        else:
            full_events.append(tr.xpath('./td/text()').get().strip())
    
    print(full_events)
    if len(events) > 0:
        print(events)
        if len(events) > 1:
            return ", ".join(events)   
        else:
            date = datetime.strptime(events[0], '%a %b %d').replace(year=datetime.now().year)
            if timedelta(days=1) > (datetime.now() - date):
                print(datetime.now() - date)
                return events[0]
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
        'Origin': 'https://volunteer.covidvaccineseattle.org',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Referer': 'https://volunteer.covidvaccineseattle.org/',
    }

    data = {
      'ctl00$ContentPlaceHolder1$ScriptManager1': 'ctl00$ContentPlaceHolder1$UpdatePanelOpKey|ctl00$ContentPlaceHolder1$DropDownListOpKey',
      '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$DropDownListOpKey',
      '__EVENTARGUMENT': '',
      '__LASTFOCUS': '',
      '__VIEWSTATE': f'{data_dict["view_state"]}',
      '__VIEWSTATEGENERATOR': 'CA0B0334',
      '__VIEWSTATEENCRYPTED': '',
      '__EVENTVALIDATION': f'{data_dict["event_validation"]}',
      'ctl00$ContentPlaceHolder1$TextBoxTitle': '',
      'ctl00$ContentPlaceHolder1$TextBoxFirstName': '',
      'ctl00$ContentPlaceHolder1$TextBoxLastName': '',
      'ctl00$ContentPlaceHolder1$TextBoxProfAbbre': '',
      'ctl00$ContentPlaceHolder1$TextBoxBadge': '',
      'ctl00$ContentPlaceHolder1$TextBoxPhone': '',
      'ctl00$ContentPlaceHolder1$TextBoxPhoneConfirm': '',
      'ctl00$ContentPlaceHolder1$DropDownListPhoneType': '-1',
      'ctl00$ContentPlaceHolder1$TextBoxAddr1': '',
      'ctl00$ContentPlaceHolder1$TextBoxAddr2': '',
      'ctl00$ContentPlaceHolder1$TextBoxCity': '',
      'ctl00$ContentPlaceHolder1$DropDownListState': '-1',
      'ctl00$ContentPlaceHolder1$TextBoxZip': '',
      'ctl00$ContentPlaceHolder1$TextBoxEmail': '',
      'ctl00$ContentPlaceHolder1$TextBoxEmail2': '',
      'ctl00$ContentPlaceHolder1$TextBoxUserName': '',
      'ctl00$ContentPlaceHolder1$TextBoxPassword': '',
      'ctl00$ContentPlaceHolder1$TextBoxPasswordVerify': '',
      'ctl00$ContentPlaceHolder1$DropDownTShirt': '-1',
      'ctl00$ContentPlaceHolder1$ListBoxLanguages': '-1',
      'ctl00$ContentPlaceHolder1$TextBoxCompanyName': '',
      'ctl00$ContentPlaceHolder1$TextBoxEmployersPlan': '',
      'ctl00$ContentPlaceHolder1$TextBoxEmergencyName': '',
      'ctl00$ContentPlaceHolder1$TextBoxEmergencyRelationship': '',
      'ctl00$ContentPlaceHolder1$TextBoxEmergencyPhone': '',
      'ctl00$ContentPlaceHolder1$DropDownListAreas': f'{data_dict["profession"]}',
      'ctl00$ContentPlaceHolder1$HiddenFieldArea': f'{data_dict["profession"]}',
      'ctl00$ContentPlaceHolder1$DropDownListProfessions': f'{data_dict["profession_ID"]}',
      'ctl00$ContentPlaceHolder1$HiddenFieldProfessionLicenseReq': '0',
      'ctl00$ContentPlaceHolder1$HiddenFieldInsuranceReq': '0',
      'ctl00$ContentPlaceHolder1$HiddenFieldIsStudentProfession': '0',
      'ctl00$ContentPlaceHolder1$TextBoxComments': '',
      'ctl00$ContentPlaceHolder1$TextBoxLicense': '',
      'ctl00$ContentPlaceHolder1$TextBoxLicenseDate': '',
      'ctl00$ContentPlaceHolder1$TextBoxLiabilityInsurance': '',
      'ctl00$ContentPlaceHolder1$DropDownListStateLicense': '-1',
      'ctl00$ContentPlaceHolder1$TextBoxLicenseComment': '',
      'ctl00$ContentPlaceHolder1$TextBoxResLocation': '',
      'ctl00$ContentPlaceHolder1$TextBoxResSupervisor': '',
      'ctl00$ContentPlaceHolder1$TextBoxSchool': '',
      'ctl00$ContentPlaceHolder1$TextBoxStudentFieldOfStudy': '',
      'ctl00$ContentPlaceHolder1$TextBoxStudentYearOfStudy': '',
      'ctl00$ContentPlaceHolder1$TextBoxFaculty': '',
      'ctl00$ContentPlaceHolder1$DropDownListStateLimit': '47',
      'ctl00$ContentPlaceHolder1$DropDownListOpKey': f'{data_dict["row_id"]}',
      'ctl00$ContentPlaceHolder1$TextBoxAdminCode': '',
      'ctl00$ContentPlaceHolder1$TextBoxDocName1': '',
      'ctl00$ContentPlaceHolder1$TextBoxDocName2': '',
      'ctl00$ContentPlaceHolder1$TextBoxDocName3': '',
      'ContentPlaceHolder1_ctlSignature_data': '',
      'ContentPlaceHolder1_ctlSignature_data_smooth': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldVolKey': '0',
      'ctl00$ContentPlaceHolder1$HiddenFieldOpAssignDayKeyList': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldAlternateOpAssignDayKeyList': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldDisplayedQuestionList': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldDisplayedAnswerList': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldWaitListed': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldSignatureFile': 'none',
      'ctl00$ContentPlaceHolder1$HiddenFieldYesValues': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldNoValues': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldDropDownValues': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldTextBoxValues': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldCommentList': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldAdminKey': '0',
      'ctl00$ContentPlaceHolder1$HiddenFieldInitialComments': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldCommentsAllowed': 'False',
      'ctl00$ContentPlaceHolder1$HiddenFieldDropDownQKey': '0',
      'ctl00$ContentPlaceHolder1$HiddenFieldShowFaculty': 'False',
      'ctl00$ContentPlaceHolder1$HiddenFieldOriginalFirstName': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldOriginalLastName': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldErrorClientIDArray': '',
      'ctl00$ContentPlaceHolder1$HiddenFieldDesktop': 'True',
      'ctl00$ContentPlaceHolder1$HiddenFieldShowMatching': 'False',
      'ctl00$ContentPlaceHolder1$HiddenFieldProfileAllowed': 'False',
      'ctl00$ContentPlaceHolder1$HiddenFieldAllowVolunteerDocuments': 'False',
      'ctl00$ContentPlaceHolder1$HiddenFieldVolDocKey': '0',
      'ctl00$ContentPlaceHolder1$HiddenFieldSignatureImageS3': '0',
      'ctl00$ContentPlaceHolder1$HiddenFieldSecretKey': '0',
      'scrollY': '2215',
      '__ASYNCPOST': 'true',
      '': ''
    }

    response = requests.post('https://volunteer.covidvaccineseattle.org/', headers=headers, data=data)
    return response