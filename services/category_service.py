from typing import Optional, List, Dict, Any
from uuid import UUID
from tortoise.exceptions import IntegrityError, DoesNotExist
from tortoise.transactions import in_transaction
from tortoise.queryset import Q

from core.logging import logger
from models.category_model import Category
from models.product_model import Product
from schemas.category_schemas import (
    CategoryCreate, 
    CategoryUpdate, 
    CategoryOut, 
    CategorySimpleOut,
    ResponseSchema
)
from schemas.filter_schemas import PaginationSchema, CategoryFilterSchema, EnhancedPaginatedResponse,FilterMetadata
from core.exceptions import (
    NotFoundException, 
    ConflictException, 
    InternalServerException
)


class CategoryService:

    # ============================
    # 🔹 CRUD BASIQUE
    # ============================

    @staticmethod
    async def create_category(
        payload: CategoryCreate, 
        return_data: bool = False
    ) -> ResponseSchema:
        """
        Crée une nouvelle catégorie avec validation souple du parent.
        Si la catégorie parente est invalide, on continue sans elle.
        """
        try:

            category_data = payload.model_dump(exclude_unset=True)

            # 🔎 Validation souple du parent
            if payload.parent_id:
                parent = await CategoryService._validate_parent_category(
                    payload.parent_id, 
                    payload.merchant_id
                )
                if not parent:
                    # Supprimer le parent_id invalide pour ne pas bloquer la création
                    category_data.pop("parent_id", None)
            
            async with in_transaction():
                category = await Category.create(**category_data)
                
                logger.info(f"Catégorie créée: {category.name} (ID: {category.id}) par {payload.merchant_id}")

                if return_data:
                    category_out = await CategoryService._enrich_category_data(category)
                    return ResponseSchema(
                        success=True,
                        message="Catégorie créée avec succès.",
                        data={"category": category_out}
                    )
                return ResponseSchema(success=True, message="Catégorie créée avec succès.")
                
        except IntegrityError as e:
            logger.warning(f"Conflit d'intégrité lors de la création: {e}")
            if "unique" in str(e).lower():
                raise ConflictException(detail="Une catégorie avec ce nom existe déjà pour ce marchand.")
            raise ConflictException(detail="Conflit de données lors de la création.")
        except Exception as e:
            logger.error(f"Erreur création catégorie: {e}")
            raise InternalServerException(detail="Erreur lors de la création de la catégorie.")

    @staticmethod
    async def get_category(category_id: UUID, include_children: bool = False) -> ResponseSchema:
        """
        Récupère une catégorie par son ID avec options d'enrichissement
        """
        try:
            category = await Category.get(id=category_id).prefetch_related("children", "parent")
            
            category_out = await CategoryService._enrich_category_data(
                category, 
                include_children=include_children
            )

            return ResponseSchema(
                success=True,
                message="Catégorie récupérée avec succès.",
                data={"category": category_out}
            )
        except DoesNotExist:
            logger.warning(f"Catégorie non trouvée: {category_id}")
            raise NotFoundException(detail="Catégorie introuvable.")
        except Exception as e:
            logger.error(f"Erreur récupération catégorie {category_id}: {e}")
            raise InternalServerException(detail="Erreur lors de la récupération de la catégorie.")

    @staticmethod
    async def list_categories(
        merchant_id: Optional[UUID] = None,
        include_global: bool = True,
        include_inactive: bool = False,
        only_with_products: bool = False,
        pagination: Optional[PaginationSchema] = None
    ) -> ResponseSchema:
        """
        Liste les catégories avec filtres avancés et pagination
        """
        try:
            query = Category.all()
            
            # Filtrage par marchand
            if merchant_id:
                if include_global:
                    query = query.filter(Q(merchant_id=merchant_id) | Q(merchant_id=None))
                else:
                    query = query.filter(merchant_id=merchant_id)
            else:
                # Si pas de merchant_id, seulement les catégories globales
                query = query.filter(merchant_id=None)

            # Filtre statut actif
            if not include_inactive:
                query = query.filter(is_active=True)

            # Préchargement des relations
            query = query.prefetch_related("children", "products","parent")

            # Pagination
            if pagination:
                total = await query.count()
                query = query.offset((pagination.page - 1) * pagination.page_size)
                query = query.limit(pagination.page_size)
            else:
                total = await query.count()

            categories = await query

            # Filtrage des catégories avec produits
            if only_with_products:
                categories = [cat for cat in categories if await cat.products.filter(is_active=True).count() > 0]

            # Enrichissement des données
            categories_data = []
            for category in categories:
                category_data = await CategoryService._enrich_category_data(category)
                categories_data.append(category_data)

            response_data = {
                "categories": categories_data,
                "total": total
            }

            if pagination:
                response_data.update({
                    "page": pagination.page,
                    "page_size": pagination.page_size,
                    "total_pages": (total + pagination.page_size - 1) // pagination.page_size
                })

            return ResponseSchema(
                success=True,
                message="Liste des catégories récupérée avec succès.",
                data=response_data
            )
        except Exception as e:
            logger.error(f"Erreur listing catégories: {e}")
            raise InternalServerException(detail="Erreur lors de la récupération des catégories.")

    @staticmethod
    async def list_categories_advanced(
        pagination: PaginationSchema,
        filters: CategoryFilterSchema
    ) -> EnhancedPaginatedResponse:
        """
        Liste avancée des catégories avec pagination et filtres
        """
        try:
            # Construction de la query de base
            query = Category.all()
            
            # Application des filtres
            if filters.search:
                query = query.filter(
                    Q(name__icontains=filters.search) | 
                    Q(description__icontains=filters.search)
                )
            
            if filters.merchant_id:
                if filters.include_global:
                    query = query.filter(
                        Q(merchant_id=filters.merchant_id) | Q(merchant_id=None)
                    )
                else:
                    query = query.filter(merchant_id=filters.merchant_id)
            
            if not filters.include_inactive:
                query = query.filter(is_active=True)
            
            if filters.parent_id:
                query = query.filter(parent_id=filters.parent_id)
            
            # Comptage total
            total = await query.count()
            
            # Application de la pagination et du tri
            categories = await query \
                .offset(pagination.offset) \
                .limit(pagination.limit) \
                .order_by(f"{pagination.sort_by}_{pagination.sort_order}") \
                .prefetch_related("children", "products")
            
            # Sérialisation des données
            categories_data = [
                await CategoryService._enrich_category_data(cat) 
                for cat in categories
            ]
            
            # Métadonnées des filtres
            filter_metadata = FilterMetadata(
                applied_filters=filters.model_dump(),
                search_query=filters.search
            )
            
            return EnhancedPaginatedResponse.create(
                data=categories_data,
                total=total,
                pagination=pagination,
                message="Catégories récupérées avec succès",
                filters=filter_metadata
            )
            
        except Exception as e:
            logger.error(f"Erreur listing avancé catégories: {e}")
            raise InternalServerException(detail="Erreur lors de la récupération des catégories.")

    @staticmethod
    async def update_category(
        category_id: UUID, 
        payload: CategoryUpdate, 
        updated_by: UUID,
        return_data: bool = False
    ) -> ResponseSchema:
        """
        Met à jour une catégorie avec validation des contraintes
        """
        try:
            category = await Category.get(id=category_id).prefetch_related("children", "products")
            
            # Validation de la hiérarchie
            update_data = payload.model_dump(exclude_unset=True)
            if 'parent_id' in update_data and update_data['parent_id']:
                await CategoryService._validate_parent_category(
                    update_data['parent_id'], 
                    category.merchant_id,
                    category_id  # Exclure la catégorie courante pour éviter les cycles
                )

            async with in_transaction():
                await category.update_from_dict(update_data)
                await category.save()

                logger.info(f"Catégorie mise à jour: {category.name} (ID: {category_id}) par {updated_by}")

                if return_data:
                    category_out = await CategoryService._enrich_category_data(category)
                    return ResponseSchema(
                        success=True,
                        message="Catégorie mise à jour avec succès.",
                        data={"category": category_out}
                    )
                return ResponseSchema(success=True, message="Catégorie mise à jour avec succès.")
                
        except DoesNotExist:
            raise NotFoundException(detail="Catégorie introuvable.")
        except IntegrityError as e:
            logger.warning(f"Conflit mise à jour catégorie {category_id}: {e}")
            if "unique" in str(e).lower():
                raise ConflictException(detail="Une catégorie avec ce nom existe déjà.")
            raise ConflictException(detail="Conflit lors de la mise à jour.")
        except Exception as e:
            logger.error(f"Erreur mise à jour catégorie {category_id}: {e}")
            raise InternalServerException(detail="Erreur lors de la mise à jour de la catégorie.")

    @staticmethod
    async def delete_category(category_id: UUID, force: bool = False) -> ResponseSchema:
        """
        Supprime une catégorie avec gestion des dépendances
        """
        try:
            category = await Category.get(id=category_id).prefetch_related("products", "children")
            
            # Vérification des dépendances
            products_count = await category.products.filter(is_active=True).count()
            children_count = await category.children.filter(is_active=True).count()

            if not force and (products_count > 0 or children_count > 0):
                raise ConflictException(
                    detail=f"Impossible de supprimer la catégorie. "
                          f"Elle contient {products_count} produit(s) et {children_count} sous-catégorie(s). "
                          f"Utilisez force=true pour forcer la suppression."
                )

            async with in_transaction():
                # Soft delete des produits associés
                if products_count > 0:
                    await category.products.filter(is_active=True).update(is_active=False)
                
                # Soft delete des sous-catégories
                if children_count > 0:
                    await category.children.filter(is_active=True).update(is_active=False)
                
                # Soft delete de la catégorie
                await category.soft_delete()

                logger.info(f"Catégorie supprimée: {category.name} (ID: {category_id})")

            return ResponseSchema(
                success=True, 
                message="Catégorie supprimée avec succès."
            )
                
        except DoesNotExist:
            raise NotFoundException(detail="Catégorie introuvable.")
        except ConflictException:
            raise  # On relance tel quel
        except Exception as e:
            logger.error(f"Erreur suppression catégorie {category_id}: {e}")
            raise InternalServerException(detail="Erreur lors de la suppression de la catégorie.")

    # ============================
    # 🔹 MÉTHODES AVANCÉES
    # ============================

    @staticmethod
    async def get_category_tree(
        merchant_id: Optional[UUID] = None, 
        include_global: bool = True
    ) -> ResponseSchema:
        """
        Retourne l'arborescence complète des catégories
        """
        try:
            query = Category.filter(is_active=True)
            
            if merchant_id:
                if include_global:
                    query = query.filter(Q(merchant_id=merchant_id) | Q(merchant_id=None))
                else:
                    query = query.filter(merchant_id=merchant_id)
            else:
                query = query.filter(merchant_id=None)

            categories = await query.prefetch_related("children", "products")
            
            # Construction de l'arbre
            root_categories = [cat for cat in categories if cat.parent_id is None]
            tree = await CategoryService._build_category_tree(root_categories, categories)

            return ResponseSchema(
                success=True,
                message="Arborescence des catégories récupérée avec succès.",
                data={"categories_tree": tree}
            )
        except Exception as e:
            logger.error(f"Erreur construction arbre catégories: {e}")
            raise InternalServerException(detail="Erreur lors de la construction de l'arborescence.")

    @staticmethod
    async def list_categories_with_products(
        merchant_id: Optional[UUID] = None,
        include_global: bool = False,
        include_inactive_categories: bool = False,
        include_inactive_products: bool = False,
        pagination: Optional[PaginationSchema] = None
    ) -> ResponseSchema:
        """
        Liste paginée des catégories avec leurs produits
        (pagination basée sur les catégories, pas sur les produits)
        """
        try:
            # --- Base query des catégories ---
            query = Category.all()

            # Filtrage par marchand
            if merchant_id:
                if include_global:
                    query = query.filter(Q(merchant_id=merchant_id) | Q(merchant_id=None))
                else:
                    query = query.filter(merchant_id=merchant_id)
            else:
                query = query.filter(merchant_id=None)

            # Filtrage par statut
            if not include_inactive_categories:
                query = query.filter(is_active=True)

            # Préchargement
            query = query.prefetch_related("children", "products", "parent")

            # Pagination basée sur les catégories
            total_categories = await query.count()
            if pagination:
                offset = (pagination.page - 1) * pagination.page_size
                query = query.offset(offset).limit(pagination.page_size)

            categories = await query

            # --- Construction des données enrichies ---
            categories_data = []
            for category in categories:
                category_data = await CategoryService._enrich_category_data(category)

                # Filtrage des produits
                products_query = category.products.all()
                if not include_inactive_products:
                    products_query = products_query.filter(is_active=True)

                products = await products_query
                products_data = [await CategoryService._serialize_product(p) for p in products]

                category_data["products"] = products_data
                category_data["products_count"] = len(products_data)

                categories_data.append(category_data)

            # --- Calcul des pages ---
            total_pages = (total_categories + pagination.page_size - 1) // pagination.page_size if pagination else 1

            # --- Réponse finale ---
            response_data = {
                "categories": categories_data,
                "total_categories": total_categories,
                "page": pagination.page if pagination else 1,
                "page_size": pagination.page_size if pagination else total_categories,
                "total_pages": total_pages
            }

            return ResponseSchema(
                success=True,
                message="Catégories avec produits récupérées avec succès.",
                data=response_data
            )

        except Exception as e:
            logger.error(f"Erreur lors du listing des catégories avec produits: {e}")
            raise InternalServerException(detail="Erreur lors de la récupération des données.")


    @staticmethod
    async def bulk_update_categories(
        updates: List[Dict[str, Any]], 
        updated_by: UUID
    ) -> ResponseSchema:
        """
        Met à jour plusieurs catégories en une seule transaction
        """
        try:
            async with in_transaction():
                updated_count = 0
                for update in updates:
                    category_id = update.get('id')
                    if not category_id:
                        continue
                    
                    try:
                        category = await Category.get(id=category_id)
                        update_data = {k: v for k, v in update.items() if k != 'id'}
                        await category.update_from_dict(update_data)
                        await category.save()
                        updated_count += 1
                    except DoesNotExist:
                        logger.warning(f"Catégorie non trouvée pour bulk update: {category_id}")
                    except Exception as e:
                        logger.error(f"Erreur bulk update catégorie {category_id}: {e}")

                logger.info(f"Bulk update: {updated_count} catégories mises à jour par {updated_by}")

                return ResponseSchema(
                    success=True,
                    message=f"{updated_count} catégorie(s) mise(s) à jour avec succès."
                )
        except Exception as e:
            logger.error(f"Erreur bulk update catégories: {e}")
            raise InternalServerException(detail="Erreur lors de la mise à jour en lot.")

    @staticmethod
    async def search_categories(
        query: str,
        merchant_id: Optional[UUID] = None,
        limit: int = 20
    ) -> ResponseSchema:
        """
        Recherche de catégories par nom ou description
        """
        try:
            search_query = Category.filter(
                Q(name__icontains=query) | Q(description__icontains=query),
                is_active=True
            )

            if merchant_id:
                search_query = search_query.filter(
                    Q(merchant_id=merchant_id) | Q(merchant_id=None)
                )

            categories = await search_query.limit(limit).prefetch_related("products")
            
            categories_data = []
            for category in categories:
                category_data = await CategoryService._enrich_category_data(category)
                categories_data.append(category_data)

            return ResponseSchema(
                success=True,
                message="Recherche de catégories effectuée avec succès.",
                data={
                    "categories": categories_data,
                    "search_query": query,
                    "total_results": len(categories_data)
                }
            )
        except Exception as e:
            logger.error(f"Erreur recherche catégories '{query}': {e}")
            raise InternalServerException(detail="Erreur lors de la recherche.")

    # ============================
    # 🔹 MÉTHODES PRIVÉES
    # ============================

    @staticmethod
    async def _validate_parent_category(
        parent_id: UUID, 
        merchant_id: Optional[UUID], 
        exclude_id: Optional[UUID] = None
    ) -> Optional[Category]:
        """
        Valide qu'une catégorie parente existe et est compatible.
        Si la catégorie est invalide ou inexistante, on log un warning
        et retourne None pour indiquer qu'elle doit être ignorée.
        """
        try:
            parent = await Category.get(id=parent_id)

            if not parent.is_active:
                logger.warning(f"Catégorie parente {parent_id} inactive — ignorée.")
                return None

            # Vérification de compatibilité du marchand
            if parent.merchant_id != merchant_id:
                logger.warning(
                    f"Incohérence: catégorie parente {parent_id} appartient à un autre marchand. Ignorée."
                )
                return None

            # Vérification des cycles (la parente ne doit pas être un descendant)
            if exclude_id:
                current = parent
                while current.parent_id:
                    if current.parent_id == exclude_id:
                        logger.warning(
                            f"Cycle détecté entre {exclude_id} et {parent_id}. Catégorie parente ignorée."
                        )
                        return None
                    current = await Category.get(id=current.parent_id)

            return parent

        except DoesNotExist:
            logger.warning(f"Catégorie parente {parent_id} introuvable — supprimée du payload.")
            return None

        except Exception as e:
            logger.warning(f"Erreur inattendue lors de la validation du parent {parent_id}: {e}")
            return None

    @staticmethod
    async def _enrich_category_data(category: Category, include_children: bool = True) -> Dict[str, Any]:
        """
        Enrichit les données d'une catégorie avec des informations calculées
        """
        category_dict = CategoryOut.model_validate(category).model_dump()
        
        # Compteur de produits actifs
        products_count = await category.products.filter(is_active=True).count()
        category_dict["products_count"] = products_count
        
        # Données des enfants si demandé
        if include_children and hasattr(category, 'children'):
            children_data = []
            for child in category.children:
                if child.is_active:
                    child_data = await CategoryService._enrich_category_data(child, include_children=False)
                    children_data.append(child_data)
            category_dict["children"] = children_data
        
        # Données du parent
        if hasattr(category, 'parent') and category.parent:
            category_dict["parent"] = CategorySimpleOut.model_validate(category.parent).model_dump()
        
        return category_dict

    @staticmethod
    async def _build_category_tree(
        root_categories: List[Category], 
        all_categories: List[Category]
    ) -> List[Dict[str, Any]]:
        """
        Construit récursivement l'arborescence des catégories
        """
        tree = []
        
        for category in root_categories:
            node = await CategoryService._enrich_category_data(category, include_children=False)
            
            # Recherche des enfants directs
            children = [cat for cat in all_categories if cat.parent_id == category.id]
            if children:
                node["children"] = await CategoryService._build_category_tree(children, all_categories)
            else:
                node["children"] = []
                
            tree.append(node)
            
        return tree

    @staticmethod
    async def _serialize_product(product: Product) -> Dict[str, Any]:
        """
        Sérialise un produit pour les réponses
        """
        return {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "currency": product.currency,
            "is_available": product.is_available,
            "stock_quantity": product.stock_quantity,
            "image_urls": product.image_urls or [],
            "sku": product.sku,
            "has_discount": product.compare_at_price is not None and product.compare_at_price > product.price,
            "is_low_stock": product.stock_quantity <= (product.low_stock_threshold or 5)
        }

    # ============================
    # 🔹 MÉTHODES STATISTIQUES
    # ============================

    @staticmethod
    async def get_categories_stats(merchant_id: Optional[UUID] = None) -> ResponseSchema:
        """
        Retourne des statistiques sur les catégories
        """
        try:
            query = Category.filter(is_active=True)
            if merchant_id:
                query = query.filter(Q(merchant_id=merchant_id) | Q(merchant_id=None))

            categories = await query.prefetch_related("products")
            
            total_categories = len(categories)
            categories_with_products = 0
            total_products = 0
            products_by_category = []

            for category in categories:
                products_count = await category.products.filter(is_active=True).count()
                if products_count > 0:
                    categories_with_products += 1
                    total_products += products_count
                    products_by_category.append({
                        "category_id": category.id,
                        "category_name": category.name,
                        "products_count": products_count
                    })

            stats = {
                "total_categories": total_categories,
                "categories_with_products": categories_with_products,
                "empty_categories": total_categories - categories_with_products,
                "total_products": total_products,
                "products_by_category": sorted(products_by_category, key=lambda x: x["products_count"], reverse=True)[:10]  # Top 10
            }

            return ResponseSchema(
                success=True,
                message="Statistiques des catégories récupérées avec succès.",
                data={"stats": stats}
            )
        except Exception as e:
            logger.error(f"Erreur calcul statistiques catégories: {e}")
            raise InternalServerException(detail="Erreur lors du calcul des statistiques.")