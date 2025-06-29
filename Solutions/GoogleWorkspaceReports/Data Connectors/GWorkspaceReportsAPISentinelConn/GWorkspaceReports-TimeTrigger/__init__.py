from __future__ import print_function
import pickle
from googleapiclient.discovery import build
import json
import base64
import hashlib
import hmac
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import azure.functions as func
import logging
import os
import time
import re
from .state_manager import StateManager
from .state_manager import AzureStorageQueueHelper
from datetime import datetime, timedelta


customer_id = os.environ['WorkspaceID']
fetchDelay = os.getenv('FetchDelay',10)
chunksize = 9999
calendarFetchDelay = os.getenv('CalendarFetchDelay',6)
chatFetchDelay = os.getenv('ChatFetchDelay',1)
userAccountsFetchDelay = os.getenv('UserAccountsFetchDelay',3)
loginFetchDelay = os.getenv('LoginFetchDelay',6)
shared_key = os.environ['WorkspaceKey']
connection_string = os.environ['AzureWebJobsStorage']
logAnalyticsUri = os.environ.get('logAnalyticsUri')
max_time_window_per_api_call_mins = os.getenv('max_time_window_per_api_call',5)

MAX_QUEUE_MESSAGES_MAIN_QUEUE = 1000
MAX_SCRIPT_EXEC_TIME_MINUTES = 3
TIME_WINDOW_To_POLL_API = 60 * int(max_time_window_per_api_call_mins)    # in seconds
SCOPES = ['https://www.googleapis.com/auth/admin.reports.audit.readonly']

activities = [
            "user_accounts",
            "access_transparency", 
            "admin",
            "calendar",
            "chat",
            "drive",
            "gcp",
            "gplus",
            "groups",
            "groups_enterprise",
            "jamboard", 
            "login", 
            "meet", 
            "mobile", 
            "rules", 
            "saml", 
            "token", 
            "context_aware_access", 
            "chrome", 
            "data_studio"
            ]

# Remove excluded activities
excluded_activities = os.environ.get('ExcludedActivities')
if excluded_activities:
    excluded_activities = excluded_activities.replace(" ", "").split(",")
    activities = [activ for activ in activities if activ not in excluded_activities]


if ((logAnalyticsUri in (None, '') or str(logAnalyticsUri).isspace())):
    logAnalyticsUri = 'https://' + customer_id + '.ods.opinsights.azure.com'
pattern = r'https:\/\/([\w\-]+)\.ods\.opinsights\.azure.([a-zA-Z\.]+)$'
match = re.match(pattern,str(logAnalyticsUri))
if(not match):
    raise Exception("Google Workspace Reports: Invalid Log Analytics Uri.")



def GetEndTime(logType):
    end_time = datetime.utcnow().replace(second=0, microsecond=0)
    if logType == "calendar":
        end_time = (end_time - timedelta(hours=int(calendarFetchDelay)))
        logging.info("End time for activity {} after fetch delay {} hour(s) applied - {}".format(logType,int(calendarFetchDelay),end_time))
    elif logType == "chat":
        end_time = (end_time - timedelta(days=int(chatFetchDelay)))
        logging.info("End time for activity {} after fetch delay {} day(s) applied - {}".format(logType,int(chatFetchDelay),end_time))
    elif logType == "user_accounts":
        end_time = (end_time - timedelta(hours=int(userAccountsFetchDelay)))
        logging.info("End time for activity {} after fetch delay {} hour(s) applied - {}".format(logType,int(userAccountsFetchDelay),end_time))
    elif logType == "login":
        end_time = (end_time - timedelta(hours=int(loginFetchDelay)))
        logging.info("End time for activity {} after fetch delay {} hour(s) applied - {}".format(logType,int(loginFetchDelay),end_time))
    else:
        end_time = (end_time - timedelta(minutes=int(fetchDelay)))
        logging.info("End time for activity {} after default fetch delay {} minute(s) applied - {}".format(logType,int(fetchDelay),end_time))
    return end_time

def isBlank (myString):
    return not (myString and myString.strip())

def isNotBlank (myString):
    return bool(myString and myString.strip())

def is_json(myjson):
    try:
        json.loads(myjson)
    except ValueError as e:
        return False
    return True

def is_valid_datetime(input):
    try:
        datetime.strptime(input, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        return False
    return True

# Function to convert string to datetime
def convertToDatetime(date_time,format):
    #format = '%b %d %Y %I:%M%p'  # The format
    datetime_str = datetime.strptime(date_time, format) 
    return datetime_str

def GetDates(logType):
    end_time_dt_obj = GetEndTime(logType) # Renamed for clarity, this is a datetime object
    state = StateManager(connection_string=connection_string)
    past_time_str_from_state = state.get() # This is a string from the state file, or None
    
    # activity_json_str will hold the JSON string representing the dictionary of activity timestamps
    activity_json_str = "" 

    # Default start time if no valid state or specific activity timestamp is found
    # Use end_time_dt_obj for this calculation, as it's the relevant end time for the current GetDates call
    default_initial_timestamp_str = (end_time_dt_obj - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + 'Z'

    if past_time_str_from_state and len(past_time_str_from_state) > 0:
        if is_json(past_time_str_from_state):
            try:
                decoded_past_time = json.loads(past_time_str_from_state)
                if isinstance(decoded_past_time, dict):
                    # The state is a valid JSON dictionary, use it.
                    # Ensure all known activities have an entry, initialize if not.
                    for activity_key in activities:
                        if activity_key not in decoded_past_time:
                            decoded_past_time[activity_key] = default_initial_timestamp_str
                    activity_json_str = json.dumps(decoded_past_time)
                else:
                    # The state was valid JSON, but not a dictionary (e.g., "123" or "\"a string\"").
                    # This is an invalid state format; reinitialize all activities.
                    temp_dict = {}
                    for activity_key_init in activities:
                        temp_dict[activity_key_init] = default_initial_timestamp_str
                    activity_json_str = json.dumps(temp_dict)
            except json.JSONDecodeError as e:
                # is_json passed, but json.loads failed. This should be rare.
                logging.error(f"Failed to decode JSON from state (is_json was true): {past_time_str_from_state}. Error: {e}. Re-initializing.")
                temp_dict = {}
                for activity_key_init in activities:
                    temp_dict[activity_key_init] = default_initial_timestamp_str
                activity_json_str = json.dumps(temp_dict)
        else:
            # past_time_str_from_state is not JSON, try legacy format conversion (single timestamp for all activities)
            temp_dict = {}
            try:
                newtime = datetime.strptime(past_time_str_from_state[:-1] + '.000Z', "%Y-%m-%dT%H:%M:%S.%fZ")
                newtime_str = newtime.strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + 'Z'
                for activity_key_init in activities:
                    temp_dict[activity_key_init] = newtime_str
                activity_json_str = json.dumps(temp_dict)
            except Exception as err:
                logging.error("Error while converting legacy state. Its neither a json nor a valid date format: {}. Error: {}".format(past_time_str_from_state, err))
                logging.info("Setting start time to get events for last 5 minutes for all activities.")
                for activity_key_init in activities:
                    temp_dict[activity_key_init] = default_initial_timestamp_str
                activity_json_str = json.dumps(temp_dict)
    else:
        # No past_time state found or it's empty. Initialize all activities.
        logging.info("No valid last time point in state, initializing all activities to fetch events for last 5 minutes.")
        temp_dict = {}
        for activity_key_init in activities:
            temp_dict[activity_key_init] = default_initial_timestamp_str
        activity_json_str = json.dumps(temp_dict)

    # Convert the end_time_dt_obj (datetime object) to the required string format for returning
    final_end_time_str = end_time_dt_obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + 'Z'

    # activity_json_str now reliably holds a JSON string of a dictionary
    loaded_activity_dict = json.loads(activity_json_str)

    if isBlank(logType):
        # Return the entire dictionary of activity timestamps
        return loaded_activity_dict
    else:
        # Return the specific start time for the logType and the calculated end_time string
        start_time_for_logtype = loaded_activity_dict.get(logType)
        if start_time_for_logtype is None:
            # This should ideally not happen if all activities are initialized correctly
            start_time_for_logtype = default_initial_timestamp_str
        return start_time_for_logtype, final_end_time_str

def check_if_script_runs_too_long(script_start_time):
    now = int(time.time())
    duration = now - script_start_time
    max_duration = int(MAX_SCRIPT_EXEC_TIME_MINUTES * 60 * 0.9)
    return duration > max_duration            

def format_message_for_queue_and_add(start_time, end_time, activity, mainQueueHelper):
    queue_body = {}
    queue_body["start_time"] = start_time
    queue_body["end_time"] = end_time
    queue_body["activity"] = activity
    mainQueueHelper.send_to_queue(queue_body,True)
    logging.info("Added to queue: {}".format(queue_body))
    

def main(mytimer: func.TimerRequest):
    logging.getLogger().setLevel(logging.INFO)
    if mytimer.past_due:
        logging.info('The timer is past due!')
    script_start_time = int(time.time())
    logging.info('Starting GWorkspaceReport-TimeTrigger program at {}'.format(time.ctime(int(time.time()))) )
    mainQueueHelper = AzureStorageQueueHelper(connectionString=connection_string, queueName="gworkspace-queue-items")
    logging.info("Check if we already have enough backlog to process in main queue. Maxmum set is MAX_QUEUE_MESSAGES_MAIN_QUEUE: {} ".format(MAX_QUEUE_MESSAGES_MAIN_QUEUE))
    mainQueueCount = mainQueueHelper.get_queue_current_count()
    logging.info("Main queue size is {}".format(mainQueueCount))
    while (mainQueueCount ) >= MAX_QUEUE_MESSAGES_MAIN_QUEUE:
        time.sleep(15)
        if check_if_script_runs_too_long(script_start_time):
            logging.info("We already have enough messages to process. Not clearing any backlog or reading a new SQS message in this iteration.")
            return
        mainQueueCount = mainQueueHelper.get_queue_current_count()
    
    latest_timestamp = ""
    postactivity_list = GetDates("")
    for line in activities:
        if check_if_script_runs_too_long(script_start_time):
            logging.info("Some more backlog to process, but ending processing for new data for this iteration, remaining will be processed in next iteration")
            return
        try:
            start_time,end_time = GetDates(line)
            if start_time is None:
                logging.info("There is no last time point, trying to get events for last one day.")
                end_time = datetime.strptime(end_time,"%Y-%m-%dT%H:%M:%S.%fZ")
                start_time = (end_time - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                end_time = end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            logging.info("Start time: {} and End time: {} for activity {}".format(start_time,end_time,line))

            # Check if start_time  is less than current UTC time minus 180 days. If yes, then set end_time to current UTC time minus 179 days
            # Google Workspace Reports API only supports 180 days of data
            if (datetime.utcnow() - timedelta(days=180)) > datetime.strptime(start_time,"%Y-%m-%dT%H:%M:%S.%fZ"):
                logging.info("End time older than 180 days. Setting start time to current UTC time minus 179 days as Google Workspace Reports API only supports 180 days of data.")
                start_time = (datetime.utcnow() - timedelta(days=179)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                start_time = start_time[:-4] + 'Z'
            
            state = StateManager(connection_string)
            
            # check if difference between start_time and end_time is more than TIME_WINDOW_To_POLL_API, if yes, then split time window to make each call to TIME_WINDOW_To_POLL_API
            while (convertToDatetime(end_time,"%Y-%m-%dT%H:%M:%S.%fZ") - convertToDatetime(start_time,"%Y-%m-%dT%H:%M:%S.%fZ")).total_seconds() > TIME_WINDOW_To_POLL_API:
                if check_if_script_runs_too_long(script_start_time):
                    logging.info("Some more backlog to process, but ending processing for new data for this iteration, remaining will be processed in next iteration")
                    return
                loop_end_time = end_time
                # check if start_time is less than end_time. If yes, then process sending to queue
                if not(convertToDatetime(start_time,"%Y-%m-%dT%H:%M:%S.%fZ") >= convertToDatetime(end_time,"%Y-%m-%dT%H:%M:%S.%fZ")):
                    end_time = (convertToDatetime(start_time,"%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(seconds=TIME_WINDOW_To_POLL_API)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                    end_time = end_time[:-4] + 'Z' 
                    format_message_for_queue_and_add(start_time, end_time, line, mainQueueHelper)
                    #update state file
                    latest_timestamp = end_time
                    postactivity_list[line] = latest_timestamp
                    logging.info("Updating state file with latest timestamp : {} for activity {}".format(latest_timestamp, line))
                    state.post(str(json.dumps(postactivity_list)))
                    start_time = end_time
                    end_time = loop_end_time

            if (convertToDatetime(end_time,"%Y-%m-%dT%H:%M:%S.%fZ") - convertToDatetime(start_time,"%Y-%m-%dT%H:%M:%S.%fZ")).total_seconds() <= TIME_WINDOW_To_POLL_API and not(convertToDatetime(start_time,"%Y-%m-%dT%H:%M:%S.%fZ") >= convertToDatetime(end_time,"%Y-%m-%dT%H:%M:%S.%fZ")):
                format_message_for_queue_and_add(start_time, end_time, line, mainQueueHelper)
                #update state file
                latest_timestamp = end_time
                postactivity_list[line] = latest_timestamp
                logging.info("Updating state file with latest timestamp : {} for activity {}".format(latest_timestamp, line))
                state.post(str(json.dumps(postactivity_list)))

        except Exception as err:
            logging.error("Something wrong. Exception error text: {}".format(err))
            logging.error( "Error: Google Workspace Reports data connector execution failed with an internal server error.")
            raise
    logging.info('Ending GWorkspaceReport-TimeTrigger program at {}'.format(time.ctime(int(time.time()))) )

