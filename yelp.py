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
PAGE_SIZE = 3

Location_Cache = ""
Cuisine_Cache = ""
Sort_Cache = ""
Offset_Cache = 0

def get_search_parameters(latitude, longitude, cityname, cuisine, sort, nextResult, moredetails):
    global Location_Cache, Cuisine_Cache, Sort_Cache, Offset_Cache

    if not nextResult and not moredetails: # new query should clear the cache
        Location_Cache = ""
        Cuisine_Cache = ""
        Sort_Cache = ""
        Offset_Cache = 0

    print "cache values"
    print "======="
    print "location " + str(Location_Cache)
    print "cuisine " + str(Cuisine_Cache)
    print "sort "+ str(Sort_Cache)
    print "offset " + str(Offset_Cache)

    # if some parameters are none use the cache values
    if not cityname and Location_Cache:
        cityname = Location_Cache
    if not cuisine  and Cuisine_Cache:
        cuisine = Cuisine_Cache
    if not sort and Sort_Cache:
        sort = Sort_Cache

    params = {}
    if nextResult:
        Offset_Cache = Offset_Cache + PAGE_SIZE

    params["offset"] = Offset_Cache

    #See the Yelp API for more details
    if cuisine:
        params["term"] = cuisine + " restaurants"
    else:
        params["term"] = "restaurants"

    if cityname:
        params["location"] = cityname

    if latitude and longitude:
        params["ll"] = "{},{}".format(latitude,longitude)

    if sort:
        params["sort"] = sort

    params["radius_filter"] = "2000"
    params["limit"] = "5"

    # update cache
    Location_Cache = cityname
    Cuisine_Cache = cuisine
    Sort_Cache = sort

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

    latitude = None
    longitude = None
    location = None
    cuisine = None
    sort = None
    nextresult = False
    skipgrounding = False
    moredetails = False
    moredetailsType = None
    moredetailsOffset = None

    if "latitude" in pairs_dict:
        latitude = pairs_dict["latitude"]
    if "longitude" in pairs_dict:
        longitude = pairs_dict["longitude"]
    if "location" in pairs_dict:
        location = pairs_dict["location"]
    if "cuisine" in pairs_dict:
        cuisine = pairs_dict["cuisine"]
    if "sort" in pairs_dict:
        sort = pairs_dict["sort"]
    if "nextresult" in pairs_dict:
        nextresult = True
    if "skipgrounding" in pairs_dict:
        skipgrounding = True
    if "moredetails" in pairs_dict:
        moredetails = True
    if "moredetailstype" in pairs_dict:
        moredetailsType = pairs_dict["moredetailstype"]
    if "moredetailsoffset" in pairs_dict:
        moredetailsOffset = int(pairs_dict["moredetailsoffset"])


    search_parameters = get_search_parameters(latitude, longitude, location, cuisine, sort, nextresult, moredetails)
    results_json_data = get_results(search_parameters)

    parsed = json.loads(results_json_data)
    # print json.dumps(parsed, indent=4, sort_keys=True)
    filtered_businesses = process_resulting_json(parsed)

    query = construct_query(search_parameters)
    xml_response = prepare_xml_response(filtered_businesses, query, skipgrounding, moredetails, moredetailsType, moredetailsOffset)

    # logging
    print "Post Body"
    print "========="
    print post_body

    print "Search Parameters"
    print "========="
    print search_parameters

    print "results:"
    print "========="
    for dic in filtered_businesses:
        print dic["name"]

    print "xml response"
    print "========="
    print(xml_response)
    print "######################"
    print "######################"
    print ""

    return xml_response


def construct_query(pairs_dict):

    query =  pairs_dict["term"] + " in " + pairs_dict["location"]

    if pairs_dict.has_key('sort') and pairs_dict["sort"]:
        query = query + " and you prefer the results to be sorted by " + get_sort_name(pairs_dict["sort"])
    return query


def get_sort_name(code):
    name = None
    if code == "0":
        name = "Best matched"
    if code == "1":
        name = "Distance"
    if code == "2":
        name = "Highest Rated"
    return name

def process_resulting_json(parsed_dict):
    parsed_businesses = parsed_dict["businesses"]
    #print(parsed_businesses)

    acceptable_keys = ["display_phone", "id", "name", "phone", "rating", "snippet_text"]
    filtered_businesses = []

    for parsed_businesses_iter in parsed_businesses:
        filtered_parsed_dict = {}
        for acceptable_keys_values in parsed_businesses_iter.items():
            if acceptable_keys_values[0] in acceptable_keys:
                filtered_parsed_dict[acceptable_keys_values[0]] = acceptable_keys_values[1]
            elif acceptable_keys_values[0] == "location":
                display_address_list = acceptable_keys_values[1]["display_address"]
                display_address = ""
                for part in display_address_list:
                    display_address = display_address + " " + part
                filtered_parsed_dict["display_address"] = display_address.strip()

        filtered_businesses.append(filtered_parsed_dict)

    return filtered_businesses


def prepare_xml_response(filtered_businesses, query, skipgrounding, moredetails, moredetailsType, moredetailsOffset):
    response_before_prompt = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\
                        <vxml version=\"2.1\"  >\
                        <form>\
                            <block>\
                                <prompt> "

    respomse_after_prompt = """
						      </prompt>
						     <goto next=\"http://""" + HOST_NAME + ":" + str(PORT_NUMBER) + \
						"""/yelp_voice.xml#ResultOptionForm\"/>
						    </block>
						  </form>
						</vxml>
						"""
						
    if not moredetails:
	    grounding_response =  "So, You are looking for " + query
	    restaurant_response =  """
	    	<break time=\"500\" /> 
	    	What about these restaurants 
	    	<break time=\"500\" /> One  <break time=\"500\" /> """ + add_to_xml(filtered_businesses[0]["name"]) + """<break strength=\"xweak\" />  Two  <break time=\"500\" /> """ + add_to_xml(filtered_businesses[1]["name"]) + """<break strength=\"xweak\" />  Three  <break time=\"500\" /> """ + add_to_xml(filtered_businesses[2]["name"])

	    if skipgrounding:
	        result = response_before_prompt + restaurant_response + respomse_after_prompt
	    else:
	        result = response_before_prompt + grounding_response + restaurant_response + respomse_after_prompt

	    return result
    else: # more details 
    	name = filtered_businesses[moredetailsOffset - 1]["name"]
    	rating = filtered_businesses[moredetailsOffset - 1]["rating"]
    	address = filtered_businesses[moredetailsOffset - 1]["display_address"]
    	phone = format_phone(filtered_businesses[moredetailsOffset - 1]["phone"])
    	snippet = filtered_businesses[moredetailsOffset - 1]["snippet_text"]

    	prompt = ""
    	if moredetailsType == "general":
    		prompt = add_to_xml(name) + " is located at " + address + ",  and it has customer rating of " + str(rating) + ".  Phone number is " + phone + ",  and here is a sample review about the place: <break strength=\"xweak\" /> " +  add_to_xml(snippet)
    	elif moredetailsType == "address":
    		prompt = add_to_xml(name) + " is located at " + address
    	elif moredetailsType == "phone":
    		prompt = "The phone number for " + add_to_xml(name) + " is " + phone
    	elif moredetailsType == "rating":
    		prompt = add_to_xml(name) + " has customer rating of " + str(rating)
    	elif moredetailsType == "review":
    		prompt = "Here is a sample review for " + add_to_xml(name) + " <break strength=\"xweak\" /> " + add_to_xml(snippet)	

    	return response_before_prompt + prompt + respomse_after_prompt

def format_phone (phonenumber):
    formatted = ""
    for c in phonenumber:
        formatted = formatted + " " + c
    return formatted.strip()


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

        post_response = parse_post_body(post_body)
        post_response = post_response.encode('utf-8').strip()
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