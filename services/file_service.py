# =========================
# Fichier : storage_utils.py
# =========================

# MinIO SDK
from minio import Minio

# FastAPI
from fastapi import UploadFile, HTTPException, status

# Utilitaires Python
import uuid
from io import BytesIO


# Config & Logging
from core.config import settings
from core.logging import logger

# Optionnel pour Boto3 (S3) si tu veux switcher plus tard
# import boto3
# from botocore.exceptions import ClientError

# =========================
# Client MinIO
# =========================

MINIO_CLIENT = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)

# =========================
# Fonction d'upload
# =========================

async def upload_identity_document(file: UploadFile) -> str:
    """
    Upload un document d'identité vers MinIO et retourne l'URL publique.
    """
    BUCKET_NAME = settings.MINIO_BUCKET_DELIVERER_IDENTITY

    try:
        # Génère un nom unique
        file_extension = file.filename.split(".")[-1]
        file_name = f"{uuid.uuid4()}.{file_extension}"

        # Vérifie ou crée le bucket
        if not MINIO_CLIENT.bucket_exists(BUCKET_NAME):
            MINIO_CLIENT.make_bucket(BUCKET_NAME)
            logger.info(f"Bucket '{BUCKET_NAME}' créé dans MinIO")

        # Lecture du fichier en mémoire
        content = await file.read()
        content_stream = BytesIO(content)

        # Upload du fichier
        MINIO_CLIENT.put_object(
            bucket_name=BUCKET_NAME,
            object_name=file_name,
            data=content_stream,
            length=len(content),
            content_type=file.content_type
        )

        # Génère l'URL publique
        url = f"http://{settings.MINIO_ENDPOINT}/{BUCKET_NAME}/{file_name}"
        logger.info(f"Fichier uploadé avec succès : {url}")

        return url

    except Exception as e:
        logger.error(f"Erreur lors de l'upload du fichier : {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'upload du fichier : {str(e)}"
        )


# =========================
# Option : upload via Boto3 (S3)
# =========================
# def upload_identity_document_s3(file: UploadFile) -> str:
#     """
#     Fonction alternative pour uploader via Boto3 (AWS S3 ou MinIO S3-compatible)
#     """
#     try:
#         s3_client = boto3.client(
#             "s3",
#             endpoint_url=settings.MINIO_ENDPOINT,
#             aws_access_key_id=settings.MINIO_ACCESS_KEY,
#             aws_secret_access_key=settings.MINIO_SECRET_KEY,
#         )
#         file_name = f"{uuid.uuid4()}.{file.filename.split('.')[-1]}"
#         s3_client.upload_fileobj(file.file, settings.MINIO_BUCKET_DELIVERER_IDENTITY, file_name)
#         url = f"{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_DELIVERER_IDENTITY}/{file_name}"
#         return url
#     except ClientError as e:
#         logger.error(f"Erreur S3 : {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Erreur S3 : {str(e)}")