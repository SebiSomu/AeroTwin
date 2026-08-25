#!/usr/bin/env python3
"""
AeroTwin S3 & CloudFront Asset Sync Utility
Uploads static assets (3D GLTF/GLB models, cached Matplotlib telemetry charts)
to Amazon S3 bucket with optimal Cache-Control and Content-Type headers.
"""

import os
import sys
import mimetypes

# Add backend directory to sys.path to reuse s3_utils
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from s3_utils import is_s3_configured, upload_file_to_s3, get_cloudfront_url
except ImportError as err:
    print(f"[Error] Could not import s3_utils: {err}")
    sys.exit(1)


def main():
    print("=" * 65)
    print("      AEROTWIN AWS S3 + CLOUDFRONT ASSET SYNC UTILITY       ")
    print("=" * 65)

    if not is_s3_configured():
        print("[!] AWS S3 is NOT configured in environment variables.")
        print("    Please set the following environment variables before running:")
        print("      - S3_BUCKET_NAME")
        print("      - AWS_ACCESS_KEY_ID")
        print("      - AWS_SECRET_ACCESS_KEY")
        print("      - AWS_REGION (optional, default: us-east-1)")
        print("      - CLOUDFRONT_DOMAIN (optional)")
        print("=" * 65)
        sys.exit(1)

    bucket = os.environ.get("S3_BUCKET_NAME")
    cf_domain = os.environ.get("CLOUDFRONT_DOMAIN", "N/A")
    print(f"[+] Target Bucket:      s3://{bucket}")
    print(f"[+] CloudFront Domain:  {cf_domain}")
    print("-" * 65)

    assets_to_sync = []

    models_dir = os.path.join(PROJECT_ROOT, "frontend", "public", "models")
    if os.path.exists(models_dir):
        for root, _, files in os.walk(models_dir):
            for file in files:
                local_path = os.path.join(root, file)
                rel_path = os.path.relpath(local_path, models_dir)
                s3_key = f"models/{rel_path}".replace("\\", "/")
                content_type = "model/gltf-binary" if file.endswith(".glb") else None
                cache_control = "public, max-age=31536000, immutable"
                assets_to_sync.append((local_path, s3_key, content_type, cache_control))

    cache_dir = os.path.join(BACKEND_DIR, "model_cache")
    if os.path.exists(cache_dir):
        for file in os.listdir(cache_dir):
            if file.endswith(".png"):
                local_path = os.path.join(cache_dir, file)
                s3_key = f"charts/{file}".replace("\\", "/")
                cache_control = "public, max-age=86400"
                assets_to_sync.append((local_path, s3_key, "image/png", cache_control))

    if not assets_to_sync:
        print("[!] No assets found to upload.")
        return

    success_count = 0
    for local_path, s3_key, content_type, cache_control in assets_to_sync:
        url = upload_file_to_s3(local_path, s3_key, content_type=content_type, cache_control=cache_control)
        if url:
            success_count += 1
            print(f"  ✓ {s3_key} -> {url}")
        else:
            print(f"  ✗ {s3_key} (Failed)")

    print("-" * 65)
    print(f"[+] Asset sync complete! Successfully synced {success_count}/{len(assets_to_sync)} files.")
    print("=" * 65)


if __name__ == "__main__":
    main()
