from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal
from tortoise.transactions import in_transaction
from tortoise.queryset import QuerySet, Q
from tortoise.expressions import F
from core.logging import logger

from models.product_model import Product
from models.category_model import Category
from schemas.product_schemas import (
    ProductCreate,
    ProductUpdate,
    ProductOut,
    ProductSimpleOut,
    ProductSummaryOut,
    ProductStockAlertOut,
    PaginatedProductsResponse
)
from schemas.filter_schemas import (
    ProductFilterSchema,
    PaginationSchema,
    DateRangeFilterSchema,
    ProductQuerySchema,
    FilterMetadata,
    EnhancedPaginatedResponse
)
from schemas.category_schemas import ResponseSchema
from core.exceptions import (
    NotFoundException,
    ConflictException,
    InternalServerException,
    BadRequestException
)


class ProductService:
    """
    Service de gestion complète des produits avec méthodes avancées :
    - CRUD complet avec validation métier
    - Gestion du stock transactionnelle
    - Recherche et filtres avancés
    - Analytics et rapports
    - Opérations en lot
    """

    # ============================
    # 🔹 CRUD COMPLET
    # ============================

    @staticmethod
    async def create_product(
        user_id: UUID,
        payload: ProductCreate,
        return_data: bool = False
    ) -> ResponseSchema:
        """
        Crée un nouveau produit avec validation complète
        """
        try:
            # Validation de la catégorie
            if payload.category_id:
                category = await Category.filter(
                    id=payload.category_id, 
                    is_active=True
                ).first()
                if not category:
                    raise BadRequestException(detail="Catégorie introuvable ou inactive")

            # Vérification unicité nom + catégorie + utilisateur
            existing_product = await Product.filter(
                name=payload.name,
                category_id=payload.category_id,
                user=user_id,
                is_active=True
            ).first()
            
            if existing_product:
                raise ConflictException(
                    detail="Un produit avec ce nom existe déjà dans cette catégorie"
                )

            # Validation SKU unique
            if payload.sku:
                sku_exists = await Product.filter(
                    sku=payload.sku,
                    is_active=True
                ).exists()
                if sku_exists:
                    raise ConflictException(detail="Un produit avec ce SKU existe déjà")

            # Préparation des données
            product_data = payload.model_dump()
            product_data["user"] = user_id
            product_data["created_by"] = user_id

            async with in_transaction():
                product = await Product.create(**product_data)
                
                logger.info(f"Produit créé: {product.name} (ID: {product.id}) par {user_id}")

                if return_data:
                    product_out = await ProductService._enrich_product_data(product)
                    return ResponseSchema(
                        success=True,
                        message="Produit créé avec succès",
                        data={"product": product_out}
                    )
                    
                return ResponseSchema(
                    success=True,
                    message="Produit créé avec succès"
                )

        except (BadRequestException, ConflictException):
            raise
        except Exception as e:
            logger.error(f"Erreur création produit: {e}")
            raise InternalServerException(detail="Erreur lors de la création du produit")

    @staticmethod
    async def get_product(
        product_id: UUID,
        include_category: bool = True,
        include_analytics: bool = False
    ) -> ResponseSchema:
        """
        Récupère un produit avec options d'enrichissement
        """
        try:
            query = Product.filter(id=product_id, is_active=True)
            
            if include_category:
                query = query.prefetch_related("category")
                
            product = await query.first()
            
            if not product:
                raise NotFoundException(detail="Produit introuvable")

            product_data = await ProductService._enrich_product_data(
                product, 
                include_analytics=include_analytics
            )

            return ResponseSchema(
                success=True,
                message="Produit récupéré avec succès",
                data={"product": product_data}
            )
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Erreur récupération produit {product_id}: {e}")
            raise InternalServerException(detail="Erreur lors de la récupération du produit")

    @staticmethod
    async def update_product(
        product_id: UUID,
        payload: ProductUpdate,
        updated_by: UUID,
        return_data: bool = False
    ) -> ResponseSchema:
        """
        Met à jour un produit avec validation des contraintes
        """
        try:
            product = await Product.filter(id=product_id, is_active=True).first()
            if not product:
                raise NotFoundException(detail="Produit introuvable")

            update_data = payload.model_dump(exclude_unset=True)
            
            # Validation des conflits de nom
            if 'name' in update_data and update_data['name'] != product.name:
                name_exists = await Product.filter(
                    name=update_data['name'],
                    category_id=product.category_id,
                    user=product.user,
                    is_active=True
                ).exclude(id=product_id).exists()
                
                if name_exists:
                    raise ConflictException(
                        detail="Un produit avec ce nom existe déjà dans cette catégorie"
                    )

            # Validation SKU unique
            if 'sku' in update_data and update_data['sku'] != product.sku:
                sku_exists = await Product.filter(
                    sku=update_data['sku'],
                    is_active=True
                ).exclude(id=product_id).exists()
                
                if sku_exists:
                    raise ConflictException(detail="Un produit avec ce SKU existe déjà")

            async with in_transaction():
                await product.update_from_dict(update_data)
                await product.save()

                logger.info(f"Produit mis à jour: {product.name} (ID: {product_id}) par {updated_by}")

                if return_data:
                    product_out = await ProductService._enrich_product_data(product)
                    return ResponseSchema(
                        success=True,
                        message="Produit mis à jour avec succès",
                        data={"product": product_out}
                    )
                    
                return ResponseSchema(
                    success=True,
                    message="Produit mis à jour avec succès"
                )

        except (NotFoundException, ConflictException):
            raise
        except Exception as e:
            logger.error(f"Erreur mise à jour produit {product_id}: {e}")
            raise InternalServerException(detail="Erreur lors de la mise à jour du produit")

    @staticmethod
    async def delete_product(product_id: UUID) -> ResponseSchema:
        """
        Soft delete d'un produit
        """
        try:
            product = await Product.filter(id=product_id, is_active=True).first()
            if not product:
                raise NotFoundException(detail="Produit introuvable")

            async with in_transaction():
                await product.soft_delete()

            logger.info(f"Produit supprimé: {product.name} (ID: {product_id})")

            return ResponseSchema(
                success=True,
                message="Produit supprimé avec succès"
            )
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Erreur suppression produit {product_id}: {e}")
            raise InternalServerException(detail="Erreur lors de la suppression du produit")

    # ============================
    # 🔹 LISTAGE ET RECHERCHE AVANCÉS
    # ============================

    @staticmethod
    async def list_products(
        query_params: ProductQuerySchema,
        user_id: Optional[UUID] = None
    ) -> EnhancedPaginatedResponse:
        """
        Liste les produits avec filtres avancés, pagination et tri
        """
        try:
            query = Product.filter(is_active=True)
            
            # Application des filtres
            query = await ProductService._apply_product_filters(query, query_params.filters, user_id)
            
            # Comptage total avant pagination
            total = await query.count()
            
            # Application pagination et tri
            products = await ProductService._apply_pagination_and_sort(
                query, 
                query_params.pagination
            ).prefetch_related("category")

            # Sérialisation des données
            products_data = [
                await ProductService._enrich_product_data(product, include_category=True)
                for product in products
            ]

            # Métadonnées des filtres
            filter_metadata = FilterMetadata(
                applied_filters=query_params.filters.model_dump(),
                search_query=query_params.filters.search,
                total_before_filtering=total  # Dans ce cas c'est le même car on a appliqué les filtres avant count
            )

            return EnhancedPaginatedResponse.create(
                data=products_data,
                total=total,
                pagination=query_params.pagination,
                message="Produits récupérés avec succès",
                filters=filter_metadata
            )

        except Exception as e:
            logger.error(f"Erreur listing produits: {e}")
            raise InternalServerException(detail="Erreur lors de la récupération des produits")

    @staticmethod
    async def search_products(
        search_term: str,
        user_id: Optional[UUID] = None,
        limit: int = 20
    ) -> ResponseSchema:
        """
        Recherche full-text dans les produits
        """
        try:
            query = Product.filter(
                is_active=True,
                is_available=True
            ).filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term) |
                Q(sku__icontains=search_term) |
                Q(tags__contains=[search_term])
            )

            if user_id:
                query = query.filter(user=user_id)

            products = await query.limit(limit).prefetch_related("category")
            
            products_data = [
                await ProductService._enrich_product_data(product, include_category=True)
                for product in products
            ]

            return ResponseSchema(
                success=True,
                message=f"Recherche '{search_term}' effectuée avec succès",
                data={
                    "products": products_data,
                    "search_term": search_term,
                    "total_results": len(products_data)
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur recherche produits '{search_term}': {e}")
            raise InternalServerException(detail="Erreur lors de la recherche")

    # ============================
    # 🔹 GESTION DU STOCK AVANCÉE
    # ============================

    @staticmethod
    async def update_stock(
        product_id: UUID,
        new_stock: int,
        reason: str = "manual_update"
    ) -> ResponseSchema:
        """
        Met à jour le stock d'un produit avec historique
        """
        try:
            if new_stock < 0:
                raise BadRequestException(detail="Le stock ne peut pas être négatif")

            async with in_transaction():
                product = await Product.filter(
                    id=product_id, 
                    is_active=True
                ).select_for_update().first()
                
                if not product:
                    raise NotFoundException(detail="Produit introuvable")

                old_stock = product.stock_quantity
                product.stock_quantity = new_stock
                product.is_available = new_stock > 0
                
                await product.save()

                logger.info(
                    f"Stock mis à jour: {product.name} "
                    f"({old_stock} → {new_stock}), raison: {reason}"
                )

            return ResponseSchema(
                success=True,
                message=f"Stock mis à jour à {new_stock} unités"
            )
            
        except (NotFoundException, BadRequestException):
            raise
        except Exception as e:
            logger.error(f"Erreur mise à jour stock {product_id}: {e}")
            raise InternalServerException(detail="Erreur lors de la mise à jour du stock")

    @staticmethod
    async def increase_stock(
        product_id: UUID,
        quantity: int,
        reason: str = "restock"
    ) -> ResponseSchema:
        """
        Augmente le stock de manière transactionnelle
        """
        try:
            if quantity <= 0:
                raise BadRequestException(detail="La quantité doit être positive")

            async with in_transaction():
                product = await Product.filter(
                    id=product_id, 
                    is_active=True
                ).select_for_update().first()
                
                if not product:
                    raise NotFoundException(detail="Produit introuvable")

                old_stock = product.stock_quantity
                product.stock_quantity += quantity
                product.is_available = True
                
                await product.save()

                logger.info(
                    f"Stock augmenté: {product.name} "
                    f"({old_stock} → {product.stock_quantity}), raison: {reason}"
                )

            return ResponseSchema(
                success=True,
                message=f"Stock augmenté de {quantity} unités"
            )
            
        except (NotFoundException, BadRequestException):
            raise
        except Exception as e:
            logger.error(f"Erreur augmentation stock {product_id}: {e}")
            raise InternalServerException(detail="Erreur lors de l'augmentation du stock")

    @staticmethod
    async def decrease_stock(
        product_id: UUID,
        quantity: int,
        reason: str = "sale"
    ) -> ResponseSchema:
        """
        Diminue le stock de manière transactionnelle avec vérification
        """
        try:
            if quantity <= 0:
                raise BadRequestException(detail="La quantité doit être positive")

            async with in_transaction():
                product = await Product.filter(
                    id=product_id, 
                    is_active=True
                ).select_for_update().first()
                
                if not product:
                    raise NotFoundException(detail="Produit introuvable")

                if product.stock_quantity < quantity:
                    raise ConflictException(
                        detail=f"Stock insuffisant. Stock actuel: {product.stock_quantity}"
                    )

                old_stock = product.stock_quantity
                product.stock_quantity -= quantity
                product.is_available = product.stock_quantity > 0
                
                await product.save()

                logger.info(
                    f"Stock diminué: {product.name} "
                    f"({old_stock} → {product.stock_quantity}), raison: {reason}"
                )

            return ResponseSchema(
                success=True,
                message=f"Stock diminué de {quantity} unités"
            )
            
        except (NotFoundException, BadRequestException, ConflictException):
            raise
        except Exception as e:
            logger.error(f"Erreur diminution stock {product_id}: {e}")
            raise InternalServerException(detail="Erreur lors de la diminution du stock")

    @staticmethod
    async def bulk_update_stock(
        updates: List[Dict[str, Any]],
        reason: str = "bulk_update"
    ) -> ResponseSchema:
        """
        Met à jour le stock de plusieurs produits en une transaction
        """
        try:
            async with in_transaction():
                updated_count = 0
                for update in updates:
                    product_id = update.get('product_id')
                    new_stock = update.get('new_stock')
                    
                    if not product_id or new_stock is None:
                        continue

                    product = await Product.filter(
                        id=product_id, 
                        is_active=True
                    ).select_for_update().first()
                    
                    if product:
                        product.stock_quantity = new_stock
                        product.is_available = new_stock > 0
                        await product.save()
                        updated_count += 1

                logger.info(f"Bulk update stock: {updated_count} produits mis à jour")

            return ResponseSchema(
                success=True,
                message=f"Stock de {updated_count} produit(s) mis à jour"
            )
            
        except Exception as e:
            logger.error(f"Erreur bulk update stock: {e}")
            raise InternalServerException(detail="Erreur lors de la mise à jour en lot du stock")

    # ============================
    # 🔹 ANALYTICS ET RAPPORTS
    # ============================

    @staticmethod
    async def get_low_stock_products(
        threshold: int = 5,
        user_id: Optional[UUID] = None
    ) -> ResponseSchema:
        """
        Liste les produits avec stock faible
        """
        try:
            query = Product.filter(
                stock_quantity__lt=threshold,
                is_active=True,
                is_available=True
            )

            if user_id:
                query = query.filter(user=user_id)

            products = await query.prefetch_related("category")
            
            low_stock_products = [
                ProductStockAlertOut(
                    product_id=product.id,
                    product_name=product.name,
                    sku=product.sku,
                    current_stock=product.stock_quantity,
                    low_stock_threshold=product.low_stock_threshold or threshold,
                    needs_restock=True
                ).model_dump()
                for product in products
            ]

            return ResponseSchema(
                success=True,
                message=f"{len(low_stock_products)} produit(s) avec stock faible",
                data={"low_stock_products": low_stock_products}
            )
            
        except Exception as e:
            logger.error(f"Erreur récupération produits stock faible: {e}")
            raise InternalServerException(detail="Erreur lors de la récupération des alertes stock")

    @staticmethod
    async def get_products_stats(
        user_id: Optional[UUID] = None,
        date_range: Optional[DateRangeFilterSchema] = None
    ) -> ResponseSchema:
        """
        Retourne des statistiques sur les produits
        """
        try:
            query = Product.filter(is_active=True)
            
            if user_id:
                query = query.filter(user=user_id)
                
            if date_range and date_range.start_date:
                # Implémentation basique - à adapter selon tes besoins
                pass

            total_products = await query.count()
            available_products = await query.filter(is_available=True).count()
            out_of_stock_products = await query.filter(stock_quantity=0).count()
            low_stock_products = await query.filter(
                stock_quantity__lt=F('low_stock_threshold'),
                stock_quantity__gt=0
            ).count()

            # Produits avec promotion
            discounted_products = await query.filter(
                compare_at_price__isnull=False,
                compare_at_price__gt=F('price')
            ).count()

            stats = {
                "total_products": total_products,
                "available_products": available_products,
                "out_of_stock_products": out_of_stock_products,
                "low_stock_products": low_stock_products,
                "discounted_products": discounted_products,
                "availability_rate": round((available_products / total_products * 100), 2) if total_products > 0 else 0
            }

            return ResponseSchema(
                success=True,
                message="Statistiques produits récupérées avec succès",
                data={"stats": stats}
            )
            
        except Exception as e:
            logger.error(f"Erreur calcul statistiques produits: {e}")
            raise InternalServerException(detail="Erreur lors du calcul des statistiques")

    # ============================
    # 🔹 MÉTHODES UTILITAIRES
    # ============================

    @staticmethod
    async def toggle_availability(product_id: UUID) -> ResponseSchema:
        """
        Active/désactive la disponibilité d'un produit
        """
        try:
            product = await Product.filter(id=product_id, is_active=True).first()
            if not product:
                raise NotFoundException(detail="Produit introuvable")

            product.is_available = not product.is_available
            await product.save()

            status_str = "activé" if product.is_available else "désactivé"
            
            logger.info(f"Disponibilité modifiée: {product.name} → {status_str}")

            return ResponseSchema(
                success=True,
                message=f"Produit {status_str} avec succès"
            )
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Erreur toggle disponibilité {product_id}: {e}")
            raise InternalServerException(detail="Erreur lors du changement de disponibilité")

    @staticmethod
    async def bulk_operations(
        operations: List[Dict[str, Any]],
        user_id: UUID
    ) -> ResponseSchema:
        """
        Exécute plusieurs opérations sur les produits en une transaction
        """
        try:
            async with in_transaction():
                results = {
                    "updated": 0,
                    "activated": 0,
                    "deactivated": 0,
                    "errors": []
                }

                for operation in operations:
                    try:
                        op_type = operation.get('operation')
                        product_id = operation.get('product_id')
                        
                        if not product_id or not op_type:
                            continue

                        product = await Product.filter(
                            id=product_id, 
                            is_active=True
                        ).first()
                        
                        if not product:
                            results["errors"].append(f"Produit {product_id} introuvable")
                            continue

                        if op_type == "activate":
                            product.is_available = True
                            await product.save()
                            results["activated"] += 1
                            
                        elif op_type == "deactivate":
                            product.is_available = False
                            await product.save()
                            results["deactivated"] += 1
                            
                        elif op_type == "update":
                            update_data = operation.get('data', {})
                            await product.update_from_dict(update_data)
                            await product.save()
                            results["updated"] += 1

                    except Exception as e:
                        results["errors"].append(f"Erreur sur {product_id}: {str(e)}")

                logger.info(f"Bulk operations: {results}")

                return ResponseSchema(
                    success=True,
                    message="Opérations en lot terminées",
                    data={"results": results}
                )
                
        except Exception as e:
            logger.error(f"Erreur bulk operations: {e}")
            raise InternalServerException(detail="Erreur lors des opérations en lot")

    # ============================
    # 🔹 MÉTHODES PRIVÉES
    # ============================

    @staticmethod
    async def _apply_product_filters(
        query: QuerySet,
        filters: ProductFilterSchema,
        user_id: Optional[UUID] = None
    ) -> QuerySet:
        """Applique les filtres avancés aux produits"""
        
        # Filtre utilisateur
        if user_id:
            query = query.filter(user=user_id)

        # Recherche texte
        if filters.search:
            query = query.filter(
                Q(name__icontains=filters.search) |
                Q(description__icontains=filters.search) |
                Q(sku__icontains=filters.search) |
                Q(tags__contains=[filters.search])
            )

        # Filtres catégorie
        if filters.category_id:
            query = query.filter(category_id=filters.category_id)
        elif filters.category_ids:
            query = query.filter(category_id__in=filters.category_ids)

        # Filtres prix
        if filters.min_price is not None:
            query = query.filter(price__gte=filters.min_price)
        if filters.max_price is not None:
            query = query.filter(price__lte=filters.max_price)

        # Filtres devise
        if filters.currency:
            query = query.filter(currency=filters.currency)

        # Filtres stock
        if filters.in_stock is not None:
            if filters.in_stock:
                query = query.filter(stock_quantity__gt=0)
            else:
                query = query.filter(stock_quantity=0)
                
        if filters.low_stock is not None:
            if filters.low_stock:
                query = query.filter(stock_quantity__lt=F('low_stock_threshold'))
            else:
                query = query.filter(stock_quantity__gte=F('low_stock_threshold'))

        # Filtres promotion
        if filters.has_discount is not None:
            if filters.has_discount:
                query = query.filter(
                    compare_at_price__isnull=False,
                    compare_at_price__gt=F('price')
                )
            else:
                query = query.filter(
                    Q(compare_at_price__isnull=True) |
                    Q(compare_at_price__lte=F('price'))
                )

        # Filtres tags
        if filters.tags:
            for tag in filters.tags:
                query = query.filter(tags__contains=[tag])

        # Filtres marchand
        if filters.merchant_id:
            # Implémentation dépendante de ta logique métier
            pass

        # Filtres disponibilité et statut
        if filters.is_available is not None:
            query = query.filter(is_available=filters.is_available)
            
        if filters.is_active is not None:
            query = query.filter(is_active=filters.is_active)

        return query

    @staticmethod
    async def _apply_pagination_and_sort(
        query: QuerySet,
        pagination: PaginationSchema
    ) -> QuerySet:
        """Applique la pagination et le tri"""
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        # Gestion du tri
        sort_field = pagination.sort_by
        if pagination.sort_order == "desc":
            sort_field = f"-{sort_field}"
            
        return query.order_by(sort_field)

    @staticmethod
    async def _enrich_product_data(
        product: Product,
        include_category: bool = False,
        include_analytics: bool = False
    ) -> Dict[str, Any]:
        """Enrichit les données du produit avec des informations calculées"""
        
        product_dict = ProductOut.from_orm(product).model_dump()
        
        # Propriétés calculées
        product_dict["has_discount"] = (
            product.compare_at_price is not None and 
            product.compare_at_price > product.price
        )
        product_dict["is_low_stock"] = (
            product.stock_quantity <= (product.low_stock_threshold or 5)
        )
        
        # Calcul pourcentage de réduction
        if product_dict["has_discount"]:
            discount = ((product.compare_at_price - product.price) / product.compare_at_price) * 100
            product_dict["discount_percentage"] = int(discount)
        else:
            product_dict["discount_percentage"] = None

        # Données de la catégorie
        if include_category and product.category:
            from schemas.category_schemas import CategorySimpleOut
            product_dict["category"] = CategorySimpleOut.from_orm(product.category).model_dump()

        # Analytics supplémentaires
        if include_analytics:
            # Ici tu pourrais ajouter des données d'analytics depuis d'autres sources
            product_dict["analytics"] = {
                "views": 0,  # À implémenter
                "sales_count": 0,  # À implémenter
                "rating": None  # À implémenter
            }

        return product_dict