from google.cloud import storage
import requests
from dateutil.relativedelta import relativedelta
import datetime
import os
import six

def slack_notification(msg):
    import requests
    import json

    url = "https://hooks.slack.com/services/"
    slack_webhook = os.environ.get('SLACK_WEBHOOK')
    payload = {"text": msg}
    headers = {'content-type': 'application/json'}

    requests.post(url+slack_webhook, data=json.dumps(payload), headers=headers)

def download():
    last_month = datetime.datetime.now() + relativedelta(months=-1)
    
    dl_filename = last_month.strftime("%y%m")

    add_url = "https://www.post.japanpost.jp/zipcode/dl/kogaki/zip/add_{0}.zip".format(
        dl_filename)
    del_url = "https://www.post.japanpost.jp/zipcode/dl/kogaki/zip/del_{0}.zip".format(
        dl_filename)

    with requests.get(add_url, stream=True) as res:
        if res.status_code == 200:
            try:
                unzip_upload(res.content)
            except:
                slack_notification("郵便番号ファイルを処理する時にエラーが発生しました。")
                return
        else:
            slack_notification("郵便番号ファイルをリクエスト時にエラー：" + res.status_code)
            return

    with requests.get(del_url, stream=True) as res:
        if res.status_code == 200:
            try:
                unzip_upload(res.content)
            except:
                slack_notification("郵便番号ファイルを処理する時にエラーが発生しました。")
                return
        else:
            slack_notification("郵便番号ファイルをリクエスト時にエラー：" + res.status_code)
            return
    
    slack_notification("郵便番号ファイルはGCSにアップロードしました。")


def unzip_upload(content):
    import io
    import zipfile
    import codecs

    with zipfile.ZipFile(io.BytesIO(content), 'r') as zip:
        for contentfilename in zip.namelist():
            with zip.open(contentfilename) as file:
                upload_file(codecs.encode(file.read().decode('shift-jis'), 'utf-8'), contentfilename, "text/csv")


def upload_file(file_stream, filename, content_type):
    """
    Uploads a file to a given Cloud Storage bucket and returns the public url
    to the new object.
    """
    # _check_extension(filename, current_app.config['ALLOWED_EXTENSIONS'])
    # filename = _safe_filename(filename)

    bucketname = os.environ.get('GOOGLE_STORAGE_BUCKET')

    # [START bookshelf_cloud_storage_client]
    client = storage.Client()
    bucket = client.bucket(bucketname)
    blob = bucket.blob(filename)

    blob.upload_from_string(
        file_stream,
        content_type=content_type)

    url = blob.public_url
    # [END bookshelf_cloud_storage_client]

    if isinstance(url, six.binary_type):
        url = url.decode('utf-8')

    return url


def transfer(*arg):
    download()


def main():
    transfer()


if __name__ == "__main__":
    main()
