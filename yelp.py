#!/usr/bin/python

import rauth
import time
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import SocketServer
import logging
import cgi
import json
from os import curdir, sep

# There are the parameters the user can search for and get information.
# Yelp json response cotnains a lot of details, filter out the unwanted 
# and reply to voice XML with just a limited set.

# Location - Send address
# Contact Information - Phone number
# Hours of Operation - Send open times  
# Type of Cuisine - Cuisine
# Menu - 
# Prices - $, $$, $$$, $$$$  
# Average User Rating - Star rating
# User Reviews -  

HOST_NAME = '104.197.18.43' # !!!REMEMBER TO CHANGE THIS!!!
PORT_NUMBER = 8081 # Maybe set this to 9000.

def get_search_parameters(latitude, longitude, cityname, cuisine):
	#See the Yelp API for more details
	params = {}
	if cuisine:
		params["term"] = cuisine + " restaurants"
	else:
		params["term"] = "restaurants"

	if cityname:
		params["location"] = cityname

	if latitude and longitude:
		params["ll"] = "{},{}".format(latitude,longitude)

	params["radius_filter"] = "2000"
	params["limit"] = "5"

	return params


def get_results(params):

	#Obtain these from Yelp's manage access page
	consumer_key = "H2auu1fDvBFJdx_0C8OsoA"
	consumer_secret = "uUhBs9q4v0-HaWvNmsb2KgJ8GP0"
	token = "CJk_pXojjW8Wavvo5UhjXvdAg7SOhkHp"
	token_secret = "7SjI2AseFjzBBPnoSnOJf0dh1eE"

	session = rauth.OAuth1Session(
		consumer_key = consumer_key
		,consumer_secret = consumer_secret
		,access_token = token
		,access_token_secret = token_secret)
	 
	request = session.get("http://api.yelp.com/v2/search",params=params)
	session.close()
	return request.text


def parse_post_body(post_body):
	pairs = post_body.split("&")
	pairs_dict = {}
	for pair in pairs:
		split_pair = pair.split("=")
		pairs_dict[split_pair[0]] = split_pair[1]

	print pairs_dict

	latitude = None
	longitude = None
	location = None
	cuisine = None

	if "latitude" in pairs_dict:
		latitude = pairs_dict["latitude"]
	if "longitude" in pairs_dict:
		longitude = pairs_dict["longitude"]
	if "location" in pairs_dict:
		location = pairs_dict["location"]
	if "cuisine" in pairs_dict:
		cuisine = pairs_dict["cuisine"]

	search_parameters = get_search_parameters(latitude, longitude, location, cuisine)
	results_json_data = get_results(search_parameters)

	parsed = json.loads(results_json_data)
	# print json.dumps(parsed, indent=4, sort_keys=True)
	filtered_businesses = process_resulting_json(parsed)
	print(filtered_businesses)

	xml_response = prepare_xml_response(filtered_businesses)
	print(xml_response)

	return xml_response


def process_resulting_json(parsed_dict):
        # {
        #     "categories": [
        #         [
        #             "Indian", 
        #             "indpak"
        #         ]
        #     ], 
        #     "display_phone": "+1-408-292-7222", 
        #     "id": "tandoori-oven-san-jose-2", 
        #     "image_url": "https://s3-media4.fl.yelpcdn.com/bphoto/OunWTteL-asypleBBfLPcA/ms.jpg", 
        #     "is_claimed": true, 
        #     "is_closed": false, 
        #     "location": {
        #         "address": [
        #             "150 S 1st St", 
        #             "Ste 107"
        #         ], 
        #         "city": "San Jose", 
        #         "coordinate": {
        #             "latitude": 37.3336334228516, 
        #             "longitude": -121.887962341309
        #         }, 
        #         "country_code": "US", 
        #         "display_address": [
        #             "150 S 1st St", 
        #             "Ste 107", 
        #             "Downtown", 
        #             "San Jose, CA 95113"
        #         ], 
        #         "geo_accuracy": 8.0, 
        #         "neighborhoods": [
        #             "Downtown"
        #         ], 
        #         "postal_code": "95113", 
        #         "state_code": "CA"
        #     }, 
        #     "menu_date_updated": 1450082133, 
        #     "menu_provider": "single_platform", 
        #     "mobile_url": "http://m.yelp.com/biz/tandoori-oven-san-jose-2?utm_campaign=yelp_api&utm_medium=api_v2_search&utm_source=H2auu1fDvBFJdx_0C8OsoA", 
        #     "name": "Tandoori Oven", 
        #     "phone": "4082927222", 
        #     "rating": 3.0, 
        #     "rating_img_url": "https://s3-media3.fl.yelpcdn.com/assets/2/www/img/34bc8086841c/ico/stars/v1/stars_3.png", 
        #     "rating_img_url_large": "https://s3-media1.fl.yelpcdn.com/assets/2/www/img/e8b5b79d37ed/ico/stars/v1/stars_large_3.png", 
        #     "rating_img_url_small": "https://s3-media3.fl.yelpcdn.com/assets/2/www/img/902abeed0983/ico/stars/v1/stars_small_3.png", 
        #     "review_count": 441, 
        #     "snippet_image_url": "http://s3-media3.fl.yelpcdn.com/photo/XO9G9J7aBH1oWv5Q8rZR2w/ms.jpg", 
        #     "snippet_text": "Food comes out fast. Prices are reasonable. The lamb korma was good but was lacking raisins and nuts. Kinda basic. Still spicy tho. The garlic naan was a...", 
        #     "url": "http://www.yelp.com/biz/tandoori-oven-san-jose-2?utm_campaign=yelp_api&utm_medium=api_v2_search&utm_source=H2auu1fDvBFJdx_0C8OsoA"
        # }

        parsed_businesses = parsed_dict["businesses"];
        print(parsed_businesses)

        acceptable_keys = ["display_phone", "id", "name", "phone", "rating"]
        filtered_businesses = []
        
        for parsed_businesses_iter in parsed_businesses:
        	filtered_parsed_dict = {}
        	for acceptable_keys_values in parsed_businesses_iter.items():
	        	if acceptable_keys_values[0] in acceptable_keys:
	        		filtered_parsed_dict[acceptable_keys_values[0]] = acceptable_keys_values[1]
	        	elif acceptable_keys_values[0] == "location":
	        		address = acceptable_keys_values[1]["address"]
	        		city = acceptable_keys_values[1]["city"]
	        		print address, city
	        		filtered_parsed_dict["address"] = address
	        		filtered_parsed_dict["city"] = city

	        filtered_businesses.append(filtered_parsed_dict)

        return filtered_businesses


def prepare_xml_response(filtered_businesses):
	response_before_prompt = """
							<?xml version="1.0" encoding="UTF-8"?>
							<vxml version="2.1">
							<form>
							  <block>
							      <prompt> """

	restaurant_response = "I found these restaurants. "

	for business in filtered_businesses:
		restaurant_response = restaurant_response + add_to_xml(business["name"]) + ". "

	respomse_after_prompt = """
							      </prompt>
							    </block>
							  </form>
							</vxml>
							"""

	concatenated_response = response_before_prompt + restaurant_response + respomse_after_prompt
	return concatenated_response


def add_to_xml(string):
	replaced_string = string.replace("&", "&amp;")
	replaced_string = replaced_string.replace("<", "&lt;")
	replaced_string = replaced_string.replace(">", "&gt;")
	replaced_string = replaced_string.replace("\'", "&apos;")
	replaced_string = replaced_string.replace("\"", "&quot;")
	return replaced_string


class myHandler(BaseHTTPRequestHandler):
	
	#Handler for the GET requests
	def do_GET(self):
		path_parts = self.path.split("?", 1)
		print("Got get request for path", path_parts[0])
		f = open(curdir + sep + path_parts[0])

		self.send_response(200)
		self.send_header('Content-type','text/html')
		self.end_headers()

		self.wfile.write(f.read())
		f.close()
		return

	def do_POST(self):
		content_len = int(self.headers.getheader('content-length', 0))
		post_body = self.rfile.read(content_len)

		print "Your name is: %s" % post_body
		post_response = parse_post_body(post_body)
		self.send_response(200)
		self.end_headers()
		self.wfile.write(post_response)
		return		


def main():
	server = HTTPServer(('', PORT_NUMBER), myHandler)
	print 'Started httpserver on port ' , PORT_NUMBER
	
	#Wait forever for incoming htto requests
	server.serve_forever()

main()
