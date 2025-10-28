# =========================
# Fichier : storage_utils.py
# =========================

from minio import Minio
import asyncio
from typing import List, Optional, Union
from fastapi import UploadFile
import uuid
from io import BytesIO

from core.config import settings
from core.logging import logger
from core.exceptions import InternalServerException, APIException


class MinioStorageV1:
    """
    Service utilitaire pour gérer le stockage de fichiers sur MinIO.
    Fournit des méthodes d'upload génériques et spécialisées.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
    ):
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.secure = secure if secure is not None else settings.MINIO_SECURE

        try:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
            logger.info(f"✅ Connexion MinIO établie sur {self.endpoint}")
        except Exception as e:
            logger.error(f"❌ Erreur de connexion à MinIO : {str(e)}")
            raise InternalServerException(detail="Impossible de se connecter à MinIO")

    # =====================
    # 🔼 Méthode principale : upload
    # =====================
    async def upload_file(
        self,
        file: UploadFile,
        bucket_name: Optional[str] = None,
        folder: Optional[str] = None,
    ) -> str:
        """
        Upload un fichier dans MinIO et retourne son URL publique.

        Args:
            file (UploadFile): Fichier à uploader
            bucket_name (Optional[str]): Nom du bucket cible
            folder (Optional[str]): Dossier logique dans le bucket

        Returns:
            str: URL publique du fichier
        """
        bucket = bucket_name or settings.MINIO_DEFAULT_BUCKET
        folder = folder.strip("/") if folder else None

        try:
            # Vérifie l’extension du fichier
            if "." not in file.filename or file.filename.startswith("."):
                raise APIException(detail="Le fichier doit avoir une extension valide (ex: .jpg, .png, .pdf).")

            file_ext = file.filename.split(".")[-1].lower()
            file_name = f"{uuid.uuid4()}.{file_ext}"
            object_path = f"{folder}/{file_name}" if folder else file_name

            # Vérifie ou crée le bucket
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info(f"🪣 Bucket '{bucket}' créé dans MinIO")

            # Lecture du contenu
            content = await file.read()
            content_stream = BytesIO(content)

            # Upload vers MinIO
            self.client.put_object(
                bucket_name=bucket,
                object_name=object_path,
                data=content_stream,
                length=len(content),
                content_type=file.content_type,
            )

            # URL publique
            url = f"http{'s' if self.secure else ''}://{self.endpoint}/{bucket}/{object_path}"
            logger.info(f"✅ Fichier uploadé avec succès : {url}")

            return url

        except APIException:
            raise
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'upload du fichier : {str(e)}")
            raise InternalServerException(detail=f"Erreur lors de l'upload du fichier : {str(e)}")

    # =====================
    # 👤 Méthode dédiée : document d'identité
    # =====================
    async def upload_identity_document(self, file: UploadFile) -> str:
        """
        Upload un document d'identité vers le bucket dédié.
        """
        bucket = settings.MINIO_BUCKET_DELIVERER_IDENTITY
        return await self.upload_file(file=file, bucket_name=bucket, folder="identity")

    # =====================
    # 🛍️ Méthode dédiée : produits marchands
    # =====================
    async def upload_product_image(self, file: UploadFile) -> str:
        """
        Upload une image de produit vers le bucket des produits.
        """
        bucket = settings.MINIO_BUCKET_MERCHANT_DOCS
        return await self.upload_file(file=file, bucket_name=bucket, folder="products")

    # =====================
    # 🛍️ Méthode dédiée : categories marchands
    # =====================
    async def upload_category_image(self, file: UploadFile) -> str:
        """
        Upload une image de categorie vers le bucket des categorie.
        """
        bucket = settings.MINIO_BUCKET_MERCHANT_DOCS
        return await self.upload_file(file=file, bucket_name=bucket, folder="categories")

class MinioStorage:
    """
    Service robuste pour gérer le stockage de fichiers sur MinIO.
    Fournit des méthodes d'upload batch et des opérations avancées.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
        max_workers: int = 5
    ):
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.secure = secure if secure is not None else settings.MINIO_SECURE
        self.max_workers = max_workers

        try:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
            logger.info(f"✅ Connexion MinIO établie sur {self.endpoint}")
        except Exception as e:
            logger.error(f"❌ Erreur de connexion à MinIO : {str(e)}")
            raise InternalServerException(detail="Impossible de se connecter à MinIO")

    # =====================
    # 🛠️ Méthodes utilitaires
    # =====================
    
    def _validate_file_extension(self, filename: str) -> None:
        """Valide l'extension du fichier."""
        if not filename or "." not in filename or filename.startswith("."):
            raise APIException(
                detail="Le fichier doit avoir une extension valide (ex: .jpg, .png, .pdf)."
            )

    def _generate_object_name(self, filename: str, folder: Optional[str] = None) -> str:
        """Génère un nom d'objet unique avec structure de dossier."""
        self._validate_file_extension(filename)
        
        file_ext = filename.split(".")[-1].lower()
        file_name = f"{uuid.uuid4()}.{file_ext}"
        
        if folder:
            folder = folder.strip("/")
            return f"{folder}/{file_name}"
        return file_name

    def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """Vérifie et crée le bucket si nécessaire."""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"🪣 Bucket '{bucket_name}' créé dans MinIO")
        except Exception as e:
            logger.error(f"❌ Erreur avec le bucket '{bucket_name}': {str(e)}")
            raise InternalServerException(detail=f"Erreur d'accès au bucket: {str(e)}")

    def _build_public_url(self, bucket_name: str, object_path: str) -> str:
        """Construit l'URL publique du fichier."""
        protocol = "https" if self.secure else "http"
        return f"{protocol}://{self.endpoint}/{bucket_name}/{object_path}"

    # =====================
    # 🔼 MÉTHODES PRINCIPALES
    # =====================

    async def upload_file(
        self,
        file: UploadFile,
        bucket_name: Optional[str] = None,
        folder: Optional[str] = None,
    ) -> str:
        """
        Upload un fichier dans MinIO et retourne son URL publique.

        Args:
            file (UploadFile): Fichier à uploader
            bucket_name (Optional[str]): Nom du bucket cible
            folder (Optional[str]): Dossier logique dans le bucket

        Returns:
            str: URL publique du fichier
        """
        bucket = bucket_name or settings.MINIO_DEFAULT_BUCKET

        try:
            # Validation et préparation
            object_path = self._generate_object_name(file.filename, folder)
            self._ensure_bucket_exists(bucket)

            # Lecture et upload
            content = await file.read()
            content_stream = BytesIO(content)

            self.client.put_object(
                bucket_name=bucket,
                object_name=object_path,
                data=content_stream,
                length=len(content),
                content_type=file.content_type or "application/octet-stream",
            )

            # Construction de l'URL
            url = self._build_public_url(bucket, object_path)
            logger.info(f"✅ Fichier '{file.filename}' uploadé avec succès: {url}")

            return url

        except APIException:
            raise
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'upload de '{file.filename}': {str(e)}")
            raise InternalServerException(
                detail=f"Erreur lors de l'upload du fichier {file.filename}: {str(e)}"
            )

    async def upload_files(
        self,
        files: List[UploadFile],
        bucket_name: Optional[str] = None,
        folder: Optional[str] = None,
        max_concurrent: Optional[int] = None
    ) -> List[str]:
        """
        Upload multiple de fichiers en parallèle.

        Args:
            files (List[UploadFile]): Liste des fichiers à uploader
            bucket_name (Optional[str]): Nom du bucket cible
            folder (Optional[str]): Dossier logique dans le bucket
            max_concurrent (Optional[int]): Nombre maximum d'uploads simultanés

        Returns:
            List[str]: Liste des URLs publiques des fichiers uploadés
        """
        if not files:
            return []

        max_workers = max_concurrent or self.max_workers
        
        async def _upload_single(file: UploadFile) -> str:
            """Wrapper pour uploader un seul fichier."""
            try:
                return await self.upload_file(file, bucket_name, folder)
            except Exception as e:
                logger.error(f"❌ Échec de l'upload de '{file.filename}': {str(e)}")
                raise

        # Upload en parallèle avec limitation
        semaphore = asyncio.Semaphore(max_workers)
        
        async def _upload_with_semaphore(file: UploadFile) -> str:
            async with semaphore:
                return await _upload_single(file)

        tasks = [_upload_with_semaphore(file) for file in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Traitement des résultats
        urls = []
        errors = []

        for result, file in zip(results, files):
            if isinstance(result, Exception):
                errors.append(f"{file.filename}: {str(result)}")
            else:
                urls.append(result)

        # Log des erreurs
        if errors:
            error_msg = f"Erreurs d'upload sur {len(errors)}/{len(files)} fichiers: {', '.join(errors)}"
            logger.warning(f"⚠️ {error_msg}")

        logger.info(f"📦 Upload batch terminé: {len(urls)}/{len(files)} fichiers réussis")
        return urls

    # =====================
    # 🎯 MÉTHODES SPÉCIALISÉES
    # =====================

    async def upload_identity_documents(self, files: List[UploadFile]) -> List[str]:
        """
        Upload multiple de documents d'identité.

        Args:
            files (List[UploadFile]): Liste des documents d'identité

        Returns:
            List[str]: Liste des URLs publiques
        """
        bucket = settings.MINIO_BUCKET_DELIVERER_IDENTITY
        return await self.upload_files(files, bucket_name=bucket, folder="identity")

    async def upload_product_images(self, files: List[UploadFile]) -> List[str]:
        """
        Upload multiple d'images de produits.

        Args:
            files (List[UploadFile]): Liste des images de produits

        Returns:
            List[str]: Liste des URLs publiques
        """
        bucket = settings.MINIO_BUCKET_MERCHANT_DOCS
        return await self.upload_files(files, bucket_name=bucket, folder="products")

    async def upload_category_images(self, files: List[UploadFile]) -> List[str]:
        """
        Upload multiple d'images de catégories.

        Args:
            files (List[UploadFile]): Liste des images de catégories

        Returns:
            List[str]: Liste des URLs publiques
        """
        bucket = settings.MINIO_BUCKET_MERCHANT_DOCS
        return await self.upload_files(files, bucket_name=bucket, folder="categories")

    # =====================
    # 🔍 MÉTHODES DE VALIDATION
    # =====================

    def validate_images_count(self, files: List[UploadFile], max_count: int = 10) -> None:
        """
        Valide le nombre d'images.

        Args:
            files (List[UploadFile]): Liste des fichiers
            max_count (int): Nombre maximum autorisé

        Raises:
            APIException: Si le nombre dépasse la limite
        """
        if len(files) > max_count:
            raise APIException(
                detail=f"Trop de fichiers fournis. Maximum {max_count} autorisés."
            )

    def validate_file_types(self, files: List[UploadFile], allowed_types: List[str]) -> None:
        """
        Valide les types de fichiers.

        Args:
            files (List[UploadFile]): Liste des fichiers
            allowed_types (List[str]): Types MIME autorisés

        Raises:
            APIException: Si un fichier n'est pas autorisé
        """
        for file in files:
            if file.content_type not in allowed_types:
                raise APIException(
                    detail=f"Type de fichier non autorisé pour {file.filename}. Types autorisés: {', '.join(allowed_types)}"
                )