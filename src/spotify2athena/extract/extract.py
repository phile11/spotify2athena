import json
from datetime import datetime
import boto3
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import base64
import urllib.request
import urllib.parse
from datetime import datetime


# Initialize AWS clients
ssm = boto3.client('ssm')
s3 = boto3.client('s3')

def get_secrets():
   # Fetch credentials securely from AWS SSM Parameter Store
    response = ssm.get_parameters(
        Names=[
            '/spotify2athena/client_id', 
            '/spotify2athena/client_secret', 
            '/spotify2athena/refresh_token'
        ],
        WithDecryption=True
    )
    # Map parameters to a clean dictionary
    params = {p['Name']: p['Value'] for p in response['Parameters']}
    return (
        params['/spotify2athena/client_id'], 
        params['/spotify2athena/client_secret'], 
        params['/spotify2athena/refresh_token']
    )

def get_new_access_token(client_id, client_secret, refresh_token):
    """Performs the raw OAuth refresh request against Spotify's token endpoint"""
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode('utf-8')).decode('utf-8')
    
    # CRITICAL FIX: Directing the payload to the API token engine instead of the homepage
    url = "https://accounts.spotify.com/api/token"
    
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode('utf-8'))
        return res_data.get("access_token")

def lambda_handler(event, context):
    
        # Get credentials from SSM
    client_id, client_secret, refresh_token = get_secrets()
    access_token = get_new_access_token(client_id, client_secret, refresh_token)
       
        # Extract Playlist data from Spotify and put it into a raw data S3 bucket
    sp = spotipy.Spotify(auth=access_token)
    playlist_link = "https://open.spotify.com/playlist/0B9N1nOnhAVwbJKtCNP0Yp"
    playlist_URI = playlist_link.split("/")[-1].split("?")[0].strip()
    filename = "spotify_raw_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
    bucket = 'phile-spotify1-raw-data'
    key_path = 'to_processed/'
    
    data = sp.playlist_items(playlist_URI, additional_types='track',)
   
    s3.put_object(
        Bucket=bucket,
        Key=key_path + filename,
        Body=json.dumps(data)
    )
        
    return {
        "statusCode": 200,
        "body": json.dumps({"message": f"dropped raw data for playlist into {bucket}/{key_path}"})
    }