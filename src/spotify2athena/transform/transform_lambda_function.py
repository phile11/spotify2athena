import datetime
import json
from io import StringIO

import boto3
import pandas as pd


def album(data):
    album_list = []
    for row in data['items']:
        album_id = row['item']['album']['id']
        album_name = row['item']['album']['name']
        album_release_date = row['item']['album']['release_date']
        album_total_tracks = row['item']['album']['total_tracks']
        album_url = row['item']['album']['external_urls']['spotify']
        album_list.append({
            'album_id': album_id,
            'name': album_name,
            'release_date': album_release_date,
            'total_tracks': album_total_tracks,
            'url': album_url
        })
    return album_list

def artist(data):
    artist_list = []
    for row in data['items']:
        for artist in row['item']['artists']:
            artist_list.append({
                'artist_id': artist['id'],
                'artist_name': artist['name'],
                'external_url': artist['href']
            })
    return artist_list

def song(data):
    song_list = []
    for row in data['items']:
        song_list.append({
            'song_id': row['item']['id'],
            'song_name': row['item']['name'],
            'duration_ms': row['item']['duration_ms'],
            'url': row['item']['external_urls']['spotify'],
            'song_added': row['added_at'],
            'album_id': row['item']['album']['id'],
            'artist_id': row['item']['album']['artists'][0]['id']
        })
    return song_list

def lambda_handler(event, context):
    s3 = boto3.client("s3")
    Bucket = "phile-spotify1-raw-data"
    Key = "to_processed/"

    # List all files waiting to be processed
    response = s3.list_objects(Bucket=Bucket, Prefix=Key)
    spotify_files = [file['Key'] for file in response['Contents'] if file['Key'].endswith('.json')]

    for file_key in spotify_files:
        # Read raw JSON from S3
        response = s3.get_object(Bucket=Bucket, Key=file_key)
        content = response['Body'].read().decode('utf-8')
        data = json.loads(content)

        # Transform
        album_list = album(data)
        artist_list = artist(data)
        song_list = song(data)

        # Create DataFrames
        album_df = pd.DataFrame(album_list).drop_duplicates(subset=['album_id'])
        artist_df = pd.DataFrame(artist_list).drop_duplicates(subset=['artist_id'])
        song_df = pd.DataFrame(song_list)

        # Convert dates
        album_df['release_date'] = pd.to_datetime(album_df['release_date'], format='mixed')
        song_df['song_added'] = pd.to_datetime(song_df['song_added'])

        # Write transformed data to S3 as CSV
        timestamp = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d_%H%M%S")

        for df, name in [(album_df, "album"), (artist_df, "artist"), (song_df, "song")]:
            buffer = StringIO()
            df.to_csv(buffer, index=False)
            s3.put_object(
                Bucket="phile-spotify1-transformed-data",
                Key=f"{name}s/{name}_transformed_{timestamp}.csv",
                Body=buffer.getvalue()
            )

        # Move processed file to 'processed' folder
        copy_source = {'Bucket': Bucket, 'Key': file_key}
        s3.copy_object(Bucket=Bucket, Key=file_key.replace("to_processed", "processed"), CopySource=copy_source)
        s3.delete_object(Bucket=Bucket, Key=file_key)

    return {
        "statusCode": 200,
        "body": json.dumps("Transform complete!")
    }

