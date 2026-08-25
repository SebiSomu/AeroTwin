import os
import mimetypes

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


def _load_env_file():
    # Search in working directory, this file's folder, and parent folder
    dirs = [
        os.getcwd(),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ]
    for d in dirs:
        env_path = os.path.join(d, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k:
                                os.environ[k] = v
                break
            except Exception:
                pass

_load_env_file()


def is_s3_configured() -> bool:
    """Check whether AWS S3 credentials and bucket configuration are present."""
    if not BOTO3_AVAILABLE:
        return False
    bucket = os.environ.get("S3_BUCKET_NAME")
    region = os.environ.get("AWS_REGION", "us-east-1")
    key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    return bool(bucket and key_id and secret)


def get_cloudfront_domain() -> str:
    """Return configured CloudFront domain or fallback to S3 regional domain."""
    cf_domain = os.environ.get("CLOUDFRONT_DOMAIN", "").strip()
    if cf_domain:
        cf_domain = cf_domain.replace("https://", "").replace("http://", "").strip("/")
        return f"https://{cf_domain}"

    bucket = os.environ.get("S3_BUCKET_NAME", "")
    region = os.environ.get("AWS_REGION", "us-east-1")
    if bucket:
        return f"https://{bucket}.s3.{region}.amazonaws.com"
    return ""


def get_cloudfront_url(s3_key: str) -> str:
    """Construct full public CloudFront / S3 URL for a given key."""
    base_domain = get_cloudfront_domain()
    if not base_domain:
        return ""
    clean_key = s3_key.lstrip("/")
    return f"{base_domain}/{clean_key}"


def upload_file_to_s3(local_path: str,s3_key: str,content_type: str = None,cache_control: str = "public, max-age=86400",) -> str | None:
    """
    Upload a local file to Amazon S3 bucket with specified headers.
    Returns the public CloudFront / S3 URL on success, or None on failure/disabled.
    """
    if not is_s3_configured():
        print("[S3 Uploader] AWS S3 is not configured. Skipping S3 upload.")
        return None

    if not os.path.exists(local_path):
        print(f"[S3 Uploader] Local file not found: {local_path}")
        return None

    bucket = os.environ.get("S3_BUCKET_NAME")
    region = os.environ.get("AWS_REGION", "us-east-1")

    if not content_type:
        content_type, _ = mimetypes.guess_type(local_path)
        if not content_type:
            content_type = "application/octet-stream"

    try:
        s3_client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        )

        print(f"[S3 Uploader] Uploading {local_path} -> s3://{bucket}/{s3_key} ({content_type})...")
        extra_args = {
            "ContentType": content_type,
            "CacheControl": cache_control,
        }

        s3_client.upload_file(local_path, bucket, s3_key.lstrip("/"), ExtraArgs=extra_args)
        url = get_cloudfront_url(s3_key)
        print(f"[S3 Uploader] Upload successful! Available at: {url}")
        return url

    except (BotoCoreError, ClientError, Exception) as e:
        print(f"[S3 Uploader] Upload failed: {e}")
        return None
