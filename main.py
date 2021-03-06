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
          "Subject": "New Volunteer Opportunity.",
          "TextPart": f"{event}\nhttps://communityvaccination.org/",
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
    mailjet_key = gc_storage_utils.access_secret_version(230736833082, 'mailjetKey', 1)
    mailjet_secret = gc_storage_utils.access_secret_version(230736833082, 'mailjetSecret', 1)
    scrapy_api_key = gc_storage_utils.access_secret_version(230736833082, 'scraper_api_key', 1)

    # start scraper api client
    client = ScraperAPIClient(scrapy_api_key)

    
    # url = 'https://volunteer.covidvaccineseattle.org/'
    url = 'https://communityvaccination.org'

    # get html response
    response = html_utils.request_page(url, client)

        #retrieve past events
    old_events = gc_storage_utils.retreive_past_dates()
    old_events = old_events.groupby(['profession', 'date']).max()


    intro_string = 'There are some new volunteer opportunities available for the groups listed below:\n'
    message_string = ''
    #loop through professions
    for prof_code, profession in zip(['G', 'G-CP2', 'G-CP2-DE', 'MP'], ['General', 'Community Partner 2', 'CP-2: Data Entry','Medical']):
        prof_str = ''
        prof_df = old_events[old_events.index.get_level_values(0) ==prof_code]
        if len(prof_df) > 0:
            prof_df = old_events.loc[prof_code]

        # loop through available weeks, check for availability
        for opt in response.xpath('//div[@id="ContentPlaceHolder1_UpdatePanelOpKey"]').xpath('.//option')[1:]:
              new_events = html_utils.check_date(opt.xpath('.//@value').get(), 
                                                    opt.xpath('text()').get(), 
                                                    top_response=response,
                                                    old_events = prof_df,
                                                    profession= prof_code)
              if new_events:
                prof_str += f'{new_events}, '
        if len(prof_str) > 0:
            message_string += f'{profession}: {prof_str[:-2]}\n'
                # email opportunity if new event
    if len(message_string) > 0:
        email_opportunity(intro_string+message_string, mailjet_key, mailjet_secret, from_address, to_address)









def hello_pubsub(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    pub_dict = json.loads(pubsub_message)
    check_availability(pub_dict['from'], pub_dict['to'])