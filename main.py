import base64

from google.cloud import secretmanager
from scraper_api import ScraperAPIClient
from google.cloud import storage

import gc_storage_utils  
import html_utils

import os

import requests
from scrapy.http import TextResponse

from datetime import datetime, timedelta



def email_opportunity(event, api_key, api_secret, to_address='+19176993314@tmomail.net'):
    from mailjet_rest import Client
    import os

    mailjet = Client(auth=(api_key, api_secret), version='v3.1')
    data = {
      'Messages': [
        {
          "From": {
            "Email": "moeco@wholesaleexecutiveinsider.com",
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




def check_availability():
    mailjet_key = gc_storage_utils.access_secret_version(234888381105, 'mailjetKey', 1)
    mailjet_secret = gc_storage_utils.access_secret_version(234888381105, 'mailjetSecret', 1)
    scrapy_api_key = gc_storage_utils.access_secret_version(234888381105, 'scraper_api_key', 1)

    client = ScraperAPIClient(scrapy_api_key)

    
    url = 'https://volunteer.covidvaccineseattle.org/'

    response = html_utils.request_page(url, client)

    # past_events = ['SeattleU Jan 25th through 30th: Washington', 'SeattleU Jan 18th through 23rd: Washington', 'SeattleU Feb 1st through 6th: Washington', 'SeattleU Feb 8th through 13th: Washington', 'SeattleU Feb 15th through 20th: Washington']
    # past_events = ['SeattleU Jan 25th through 30th: Washington', 'SeattleU Jan 18th through 23rd: Washington', 'SeattleU Feb 1st through 6th: Washington']
    # past_events = []
    # all_events = response.xpath('//div[@id="ContentPlaceHolder1_UpdatePanelOpKey"]').xpath('.//option/text()').getall()[1:]

    # bucket = 'vaccine_checker'
    # filepath =  '/tmp/'
    # filename = 'past_weeks.txt'

    # gc_storage_utils.download_blob(bucket, filename, filepath+filename)

    # with open(filepath+filename, 'r') as reader:
    #   # Read and print the entire file line by line
    #   for line in reader:
    #       past_events.append(line.strip())

    # print(past_events)
    # for event in all_events:
    #     if event not in past_events:
    #         email_opportunity(event, mailjet_key, mailjet_secret, 'moesvaccinearmy@googlegroups.com')
    
    

    # with open(filepath+filename,  'w') as f:
    #   for event in all_events:
    #     print(f'{event}', file=f)
    # gc_storage_utils.upload_blob(bucket, filepath+filename, filename)
    for opt in response.xpath('//div[@id="ContentPlaceHolder1_UpdatePanelOpKey"]').xpath('.//option')[1:]:
      new_events = html_utils.check_date(opt.xpath('.//@value').get(), opt.xpath('text()').get(), top_response=response)
      if new_events:
        email_opportunity(event, mailjet_key, mailjet_secret, 'moesvaccinearmy@googlegroups.com')





def hello_pubsub(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    print(pubsub_message)
    check_availability()

