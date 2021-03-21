from google.cloud import storage
from google.cloud import secretmanager

from google.cloud import bigquery
from google.cloud import bigquery_storage

import google.auth


def retreive_past_dates():
	credentials, your_project_id = google.auth.default(
	    scopes=["https://www.googleapis.com/auth/cloud-platform"]
	)

	# Make clients.
	bqclient = bigquery.Client(credentials=credentials, project=your_project_id,)
	bqstorageclient = bigquery_storage.BigQueryReadClient(credentials=credentials)

	query_string = """
	SELECT * 
	FROM `vaccine-volunteering.dates_accessed.dates`
	"""

	dataframe = (
	    bqclient.query(query_string)
	    .result()
	    .to_dataframe(bqstorage_client=bqstorageclient)
	)
	return dataframe

def upload_new_dates(date_dict):
	client = bigquery.Client()

	
	errors = client.insert_rows_json('vaccine-volunteering.dates_accessed.dates', date_dict)  # Make an API request.
	if errors == []:
	    print("New rows have been added.")
	else:
	    print("Encountered errors while inserting rows: {}".format(errors))

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    # bucket_name = "your-bucket-name"
    # source_blob_name = "storage-object-name"
    # destination_file_name = "local/path/to/file"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    print(
        "Blob {} downloaded to {}.".format(
            source_blob_name, destination_file_name
        )
    )


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    # bucket_name = "your-bucket-name"
    # source_file_name = "local/path/to/file"
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(
        "File {} uploaded to {}.".format(
            source_file_name, destination_blob_name
        )
    )


def access_secret_version(project_id, secret_id, version_id):
    """
    Access the payload for the given secret version if one exists. The version
    can be a version number as a string (e.g. "5") or an alias (e.g. "latest").
    """

    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    # Access the secret version.
    response = client.access_secret_version(request={"name": name})

    # return the secret payload.
    payload = response.payload.data.decode("UTF-8")
    return payload