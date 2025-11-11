#!/bin/bash

mc alias set schrodinger http://$MINIO_HOST:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD;

# Setup user & acccess policy
mc admin user add schrodinger $ACCESS_KEY $SECRET_ACCESS_KEY
mc admin policy create schrodinger schrodinger-development $POLICY_FILE
mc admin policy attach schrodinger schrodinger-development --user $ACCESS_KEY

# Create buckets
mc mb schrodinger/$BUCKET_NAME --with-versioning --ignore-existing

mc mb schrodinger/$PUBLIC_BUCKET_NAME --with-versioning --ignore-existing
mc anonymous set download schrodinger/$PUBLIC_BUCKET_NAME

mc mb schrodinger/$BUCKET_TESTING_NAME --with-versioning --ignore-existing
