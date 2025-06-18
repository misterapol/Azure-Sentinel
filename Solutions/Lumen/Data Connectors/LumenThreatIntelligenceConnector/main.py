import datetime
import json
import logging
import os
import sys
import time
from collections import namedtuple
from typing import List, Dict, Any

import azure.functions as func
import msal
import requests
from requests.adapters import HTTPAdapter
from requests_ratelimiter import LimiterSession
from urllib3.util import Retry

REQUIRED_ENVIRONMENT_VARIABLES = [
    "LUMEN_API_KEY",
    "LUMEN_BASE_URL", 
    "CLIENT_ID",
    "CLIENT_SECRET",
    "TENANT_ID",
    "WORKSPACE_ID",
]

LumenSetup = namedtuple("LumenSetup", ["api_key", "base_url", "tries"])
MSALSetup = namedtuple("MSALSetup", ["tenant_id", "client_id", "client_secret", "workspace_id"])

class LumenSentinelUpdater(object):
    """Lumen Threat Intelligence to Microsoft Sentinel STIX Objects uploader"""

    def __init__(self, lumen_setup: LumenSetup, msal_setup: MSALSetup):
        super(LumenSentinelUpdater, self).__init__()

        self.lumen_api_key = lumen_setup.api_key
        self.lumen_base_url = lumen_setup.base_url
        self.lumen_tries = lumen_setup.tries
        self.msal_tenant_id = msal_setup.tenant_id
        self.msal_client_id = msal_setup.client_id
        self.msal_client_secret = msal_setup.client_secret
        self.msal_workspace_id = msal_setup.workspace_id

        # Setup RateLimiter and Retry Adapter - aligned with new STIX Objects API limits
        # 100 requests per minute, 100 objects per request
        self.limiter_session = LimiterSession(
            per_minute=95,  # Slightly under limit for safety
            limit_statuses=[429, 503],
        )
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS", "POST"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.limiter_session.mount("http://", adapter)
        self.limiter_session.mount("https://", adapter)

        self.bearer_token = None
        self.token_expiry_seconds = None

    def get_lumen_presigned_url(self) -> str:
        """Get presigned URL from Lumen API
        
        Returns:
            str: The presigned URL for downloading threat intelligence data
        """
        headers = {
            'Authorization': f'Bearer {self.lumen_api_key}',
            'Content-Type': 'application/json'
        }
        
        # POST request to get presigned URL
        url = f"{self.lumen_base_url}/threat-intelligence/download"
        
        try:
            response = self.limiter_session.post(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            presigned_url = data.get('downloadUrl')
            
            if not presigned_url:
                raise ValueError("No downloadUrl found in Lumen API response")
                
            logging.info(f"Successfully obtained presigned URL from Lumen API")
            return presigned_url
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error getting presigned URL from Lumen API: {e}")
            raise

    def get_lumen_threat_data(self, presigned_url: str) -> Dict[str, Any]:
        """Download threat intelligence data from Lumen presigned URL
        
        Args:
            presigned_url (str): The presigned URL from Lumen API
            
        Returns:
            Dict[str, Any]: The threat intelligence data in STIX format
        """
        try:
            response = self.limiter_session.get(presigned_url, timeout=300)  # 5 min timeout for large files
            response.raise_for_status()
            
            data = response.json()
            logging.info(f"Successfully downloaded threat data from Lumen. Data size: {len(str(data))} characters")
            
            return data
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error downloading threat data from presigned URL: {e}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing JSON response from presigned URL: {e}")
            raise

    def acquire_token(self):
        """Acquire Microsoft Entra access token using MSAL
        
        Returns:
            tuple: (bearer_token, token_expiry_seconds)
        """
        try:
            scope = ["https://management.azure.com/.default"]
            context = msal.ConfidentialClientApplication(
                self.msal_client_id, 
                authority=f"https://login.microsoftonline.com/{self.msal_tenant_id}",
                client_credential=self.msal_client_secret
            )
            
            result = context.acquire_token_silent(scopes=scope, account=None)
            if not result:
                result = context.acquire_token_for_client(scopes=scope)

            if 'access_token' in result:
                bearer_token = result['access_token']
                token_expiry_seconds = result['expires_in']
                logging.info("Successfully acquired Microsoft Entra access token")
                return bearer_token, token_expiry_seconds
            else:
                error_code = result.get("error")
                error_message = result.get("error_description")
                logging.error(f"Error acquiring token: {error_code} - {error_message}")
                raise ValueError(error_message)

        except Exception as e:
            logging.error(f"Error acquiring token: {e}")
            raise

    def upload_stix_objects_to_sentinel(self, token: str, stix_objects: List[Dict[str, Any]]) -> requests.Response:
        """Upload STIX objects to Microsoft Sentinel using the new STIX Objects API
        
        Args:
            token (str): The access token
            stix_objects (List[Dict[str, Any]]): List of STIX objects to upload
            
        Returns:
            requests.Response: The API response
        """
        # New STIX Objects API endpoint
        url = f"https://api.ti.sentinel.azure.com/workspaces/{self.msal_workspace_id}/threat-intelligence-stix-objects:upload"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        params = {
            'api-version': '2024-02-01-preview'
        }
        
        # New STIX Objects API format
        payload = {
            'sourcesystem': 'Lumen',
            'stixobjects': stix_objects
        }

        try:
            response = self.limiter_session.post(
                url, 
                headers=headers,
                params=params,
                json=payload,
                timeout=30
            )
            
            logging.info(f"Upload response status: {response.status_code}")
            
            if response.status_code == 200:
                # Check for validation errors even with 200 status
                try:
                    response_data = response.json()
                    if 'errors' in response_data:
                        logging.warning(f"Upload completed with validation errors: {response_data['errors']}")
                    else:
                        logging.info(f"Successfully uploaded {len(stix_objects)} STIX objects to Sentinel")
                except json.JSONDecodeError:
                    # Empty response body on success is normal
                    logging.info(f"Successfully uploaded {len(stix_objects)} STIX objects to Sentinel")
            else:
                logging.error(f"Upload failed with status {response.status_code}: {response.text}")
                
            return response
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error uploading STIX objects to Sentinel: {e}")
            raise

    def process_lumen_data(self) -> int:
        """Main processing function to get Lumen data and upload to Sentinel
        
        Returns:
            int: Number of STIX objects successfully processed
        """
        total_processed = 0
        
        try:
            # Step 1: Get presigned URL from Lumen API
            logging.info("Getting presigned URL from Lumen API...")
            presigned_url = self.get_lumen_presigned_url()
            
            # Step 2: Download threat data from presigned URL
            logging.info("Downloading threat intelligence data...")
            threat_data = self.get_lumen_threat_data(presigned_url)
            
            # Step 3: Extract STIX objects from the response
            stix_objects = threat_data.get('stixobjects', [])
            if not stix_objects:
                logging.warning("No STIX objects found in Lumen threat data")
                return 0
                
            logging.info(f"Found {len(stix_objects)} STIX objects in Lumen data")
            
            # Step 4: Acquire token for Sentinel API
            if not self.bearer_token:
                self.bearer_token, self.token_expiry_seconds = self.acquire_token()
            
            # Step 5: Upload STIX objects in batches (API limit: 100 objects per request)
            batch_size = 100
            for i in range(0, len(stix_objects), batch_size):
                batch = stix_objects[i:i + batch_size]
                
                logging.info(f"Uploading batch {i//batch_size + 1} ({len(batch)} objects)...")
                
                try:
                    response = self.upload_stix_objects_to_sentinel(self.bearer_token, batch)
                    
                    if response.status_code == 200:
                        total_processed += len(batch)
                        logging.info(f"Successfully uploaded batch {i//batch_size + 1}")
                    else:
                        logging.error(f"Failed to upload batch {i//batch_size + 1}: {response.status_code}")
                        
                except Exception as e:
                    logging.error(f"Error uploading batch {i//batch_size + 1}: {e}")
                    continue
                
                # Rate limiting: 100 requests per minute, so wait if needed
                time.sleep(0.7)  # Slightly over 60/100 seconds between requests
            
            logging.info(f"Processing complete. Total STIX objects processed: {total_processed}")
            return total_processed
            
        except Exception as e:
            logging.error(f"Error in process_lumen_data: {e}")
            raise


def main(mytimer: func.TimerRequest) -> None:
    """Azure Function main entry point"""
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info(f'Lumen Threat Intelligence Connector executed at: {utc_timestamp}')

    # Validate environment variables
    missing_vars = []
    for var in REQUIRED_ENVIRONMENT_VARIABLES:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logging.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)

    try:
        # Initialize configuration
        lumen_setup = LumenSetup(
            api_key=os.environ.get("LUMEN_API_KEY"),
            base_url=os.environ.get("LUMEN_BASE_URL"),
            tries=3
        )
        
        msal_setup = MSALSetup(
            tenant_id=os.environ.get("TENANT_ID"),
            client_id=os.environ.get("CLIENT_ID"),
            client_secret=os.environ.get("CLIENT_SECRET"),
            workspace_id=os.environ.get("WORKSPACE_ID")
        )

        # Initialize and run the updater
        updater = LumenSentinelUpdater(lumen_setup, msal_setup)
        processed_count = updater.process_lumen_data()
        
        logging.info(f"Lumen Threat Intelligence Connector completed successfully. "
                    f"Processed {processed_count} STIX objects.")

    except Exception as e:
        logging.error(f"Lumen Threat Intelligence Connector failed: {e}")
        sys.exit(1)
