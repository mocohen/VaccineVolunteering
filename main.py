import base64

from google.cloud import secretmanager
from scraper_api import ScraperAPIClient
from google.cloud import storage

import gc_storage_utils  
import html_utils
import json

import os

import requests
from scrapy.http import TextResponse

from datetime import datetime, timedelta



def email_opportunity(event, api_key, api_secret, from_address, to_address):
    '''
    email opportunity using mailjest rest

    Args:
        event (string): string formatted list of available events 
        api_key (string): mailjet api key
        api_secret (string): mailjet api secret
        from_address (string): from email address
        to_address (string): to email address
    '''
    from mailjet_rest import Client
    import os

    mailjet = Client(auth=(api_key, api_secret), version='v3.1')
    data = {
      'Messages': [
        {
          "From": {
            "Email": from_address,
            "Name": "Morris"
          },
          "To": [
            {
              "Email": to_address,
              "Name": "Morris"
            }
          ],
          "Subject": "New Volunteer opportunity.",
          "TextPart": f"{event}\nhttps://volunteer.covidvaccineseattle.org/",
        }
      ]
    }
    result = mailjet.send.create(data=data)
    print(result.status_code)
    print(result.json())




def check_availability(from_address, to_address):
    ''' Check for events with availability

    Args:
        from_address (string) : email address to send notifications from
        to_address (string) : email address to send notifications to

    '''

    # get secrets from google cloud
    mailjet_key = gc_storage_utils.access_secret_version(234888381105, 'mailjetKey', 1)
    mailjet_secret = gc_storage_utils.access_secret_version(234888381105, 'mailjetSecret', 1)
    scrapy_api_key = gc_storage_utils.access_secret_version(234888381105, 'scraper_api_key', 1)

    # start scraper api client
    client = ScraperAPIClient(scrapy_api_key)

    
    url = 'https://volunteer.covidvaccineseattle.org/'

    # get html response
    response = html_utils.request_page(url, client)


    # loop through available weeks, check for availability
    for opt in response.xpath('//div[@id="ContentPlaceHolder1_UpdatePanelOpKey"]').xpath('.//option')[1:]:
      new_events = html_utils.check_date(opt.xpath('.//@value').get(), opt.xpath('text()').get(), top_response=response)
      if new_events:
        # email opportunity if new event
        email_opportunity(new_events, mailjet_key, mailjet_secret, from_address, to_address)


    # testing out LA volunteer checking
    la_url = 'https://appointments.lacounty.gov/vaccinestaffing/LocationsMap'
    la_response = html_utils.request_page(la_url, client)
    prev_full_text = 'Currently, ALL of the staffing slots for Clinical and Non-Clinical roles are FULL. Please check back regularly as future dates will be added.'

    try:
      new_alert_text = la_response.xpath('//div[contains(@class, "alert-danger")]/text()').get().strip()
    except:
      new_alert_text = ''
    if prev_full_text != new_alert_text:
      email_opportunity("new LA events", mailjet_key, mailjet_secret, from_address, "+19176993314@tmomail.net")







def hello_pubsub(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    pub_dict = json.loads(pubsub_message)
    check_availability(pub_dict['from'], pub_dict['to'])