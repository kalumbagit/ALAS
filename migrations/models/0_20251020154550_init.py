from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "subscription_plans" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "code" VARCHAR(50) NOT NULL UNIQUE,
    "name" VARCHAR(100) NOT NULL,
    "description" TEXT,
    "commission_rate" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "monthly_fee" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "is_active" BOOL NOT NULL  DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "subscription_plans"."code" IS 'Code interne du plan (ex: free, basic, pro...)';
COMMENT ON COLUMN "subscription_plans"."name" IS 'Nom lisible du plan';
COMMENT ON COLUMN "subscription_plans"."description" IS 'Description du plan d’abonnement';
COMMENT ON COLUMN "subscription_plans"."commission_rate" IS 'Pourcentage prélevé sur chaque transaction';
COMMENT ON COLUMN "subscription_plans"."monthly_fee" IS 'Frais mensuels fixes pour ce plan';
COMMENT ON COLUMN "subscription_plans"."is_active" IS 'Définit si le plan est actuellement actif';
COMMENT ON TABLE "subscription_plans" IS 'Modèle représentant un plan d''abonnement disponible pour les marchands.';
CREATE TABLE IF NOT EXISTS "user" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "email" VARCHAR(254) NOT NULL UNIQUE,
    "phone" VARCHAR(15) NOT NULL UNIQUE,
    "password_hash" VARCHAR(128) NOT NULL,
    "first_name" VARCHAR(30) NOT NULL,
    "last_name" VARCHAR(30) NOT NULL,
    "user_type" VARCHAR(9) NOT NULL  DEFAULT 'customer',
    "avatar_url" VARCHAR(255),
    "is_verified" BOOL NOT NULL  DEFAULT True,
    "is_active" BOOL NOT NULL  DEFAULT True,
    "is_superuser" BOOL NOT NULL  DEFAULT False,
    "rating" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "total_ratings" INT NOT NULL  DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "user"."user_type" IS 'CUSTOMER: customer\nDELIVERER: deliverer\nMERCHANT: merchant\nADMIN: admin';
COMMENT ON TABLE "user" IS 'Représente un utilisateur de la plateforme (client, livreur, marchand, admin).';
CREATE TABLE IF NOT EXISTS "delivererdetails" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "is_online" BOOL NOT NULL  DEFAULT False,
    "is_active" BOOL NOT NULL  DEFAULT True,
    "is_suspended" BOOL NOT NULL  DEFAULT False,
    "suspension_end" TIMESTAMPTZ,
    "suspension_reason" TEXT,
    "total_earnings" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "referral_earnings" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "completed_deliveries" INT NOT NULL  DEFAULT 0,
    "identity_type" VARCHAR(18) NOT NULL  DEFAULT 'other',
    "identity_document_url" VARCHAR(255),
    "selfie_photo_url" VARCHAR(255),
    "identity_code" VARCHAR(100),
    "identity_verified" BOOL NOT NULL  DEFAULT False,
    "verification_method" VARCHAR(12) NOT NULL  DEFAULT 'manual',
    "verified_by" VARCHAR(100),
    "verification_date" TIMESTAMPTZ,
    "vehicle_type" VARCHAR(10) NOT NULL  DEFAULT 'walking',
    "current_latitude" DECIMAL(9,6),
    "current_longitude" DECIMAL(9,6),
    "referral_code" VARCHAR(20)  UNIQUE,
    "total_referrals" INT NOT NULL  DEFAULT 0,
    "pending_withdrawal_amount" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "total_withdrawn" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "last_online_update" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "sponsor_id" UUID REFERENCES "delivererdetails" ("id") ON DELETE SET NULL,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "delivererdetails"."identity_type" IS 'CNI: cni\nPASSPORT: passport\nDRIVER_LICENSE: driver_license\nELECTORAL_CARD: electoral_card\nCNI_RECEIPT: recépicé de la cni\nOTHER: other';
COMMENT ON COLUMN "delivererdetails"."verification_method" IS 'MANUAL: manual\nSELFIE_MATCH: selfie_match\nOTP_ONLY: otp_only\nSPONSORED: sponsored';
COMMENT ON COLUMN "delivererdetails"."vehicle_type" IS 'BIKE: bike\nMOTORCYCLE: motorcycle\nCAR: car\nWALKING: walking\nSCOOTER: scooter';
COMMENT ON COLUMN "delivererdetails"."pending_withdrawal_amount" IS 'Montant total en attente de retrait';
COMMENT ON COLUMN "delivererdetails"."total_withdrawn" IS 'Montant total déjà retiré';
COMMENT ON TABLE "delivererdetails" IS 'Contient les informations supplémentaires relatives à un livreur.';
CREATE TABLE IF NOT EXISTS "delivererearnings" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "delivery_reference" VARCHAR(100)  UNIQUE,
    "amount" DECIMAL(10,2) NOT NULL,
    "is_advance_payment" BOOL NOT NULL  DEFAULT False,
    "description" TEXT,
    "status" VARCHAR(10) NOT NULL  DEFAULT 'pending',
    "payment_date" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "deliverer_id" UUID NOT NULL REFERENCES "delivererdetails" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "delivererearnings"."delivery_reference" IS 'Identifiant de la livraison associée (non lié directement)';
COMMENT ON COLUMN "delivererearnings"."is_advance_payment" IS 'True si payé à l''avance';
COMMENT ON COLUMN "delivererearnings"."description" IS 'Motif ou détail du paiement';
COMMENT ON COLUMN "delivererearnings"."status" IS 'Statut du paiement';
COMMENT ON TABLE "delivererearnings" IS 'Représente les gains du livreur, incluant les paiements anticipés,';
CREATE TABLE IF NOT EXISTS "delivererwithdrawal" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "amount" DECIMAL(10,2) NOT NULL,
    "reference" VARCHAR(100) NOT NULL UNIQUE,
    "status" VARCHAR(9) NOT NULL  DEFAULT 'PENDING',
    "method" VARCHAR(13) NOT NULL  DEFAULT 'MOBILE_MONEY',
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "processed_at" TIMESTAMPTZ,
    "deliverer_id" UUID NOT NULL REFERENCES "delivererdetails" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "delivererwithdrawal"."reference" IS 'Référence unique du retrait';
COMMENT ON COLUMN "delivererwithdrawal"."status" IS 'Statut du retrait';
COMMENT ON COLUMN "delivererwithdrawal"."method" IS 'Méthode de retrait utilisée';
COMMENT ON COLUMN "delivererwithdrawal"."processed_at" IS 'Date effective du retrait';
COMMENT ON TABLE "delivererwithdrawal" IS 'Historique des retraits effectués par un livreur.';
CREATE TABLE IF NOT EXISTS "merchant" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "business_name" VARCHAR(100) NOT NULL,
    "business_type" VARCHAR(11) NOT NULL  DEFAULT 'other',
    "description" TEXT,
    "logo_url" VARCHAR(255),
    "banner_url" VARCHAR(255),
    "siret" VARCHAR(50) NOT NULL UNIQUE,
    "commission_balance" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "last_payment_date" TIMESTAMPTZ,
    "is_approved" BOOL NOT NULL  DEFAULT False,
    "is_verified" BOOL NOT NULL  DEFAULT False,
    "rating" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "total_ratings" INT NOT NULL  DEFAULT 0,
    "is_active" BOOL NOT NULL  DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "subscription_plan_id" UUID REFERENCES "subscription_plans" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "merchant"."business_type" IS 'RESTAURANT: restaurant\nGROCERY: grocery\nSUPERMARKET: supermarket\nBOUTIQUE: boutique\nPHARMACY: pharmacy\nELECTRONICS: electronics\nFASHION: fashion\nBEAUTY: beauty\nBAKERY: bakery\nBOOKSTORE: bookstore\nHARDWARE: hardware\nOTHER: other';
COMMENT ON COLUMN "merchant"."commission_balance" IS 'Total des commissions dues/non payées';
COMMENT ON TABLE "merchant" IS 'Représente un marchand enregistré dans la plateforme.';
CREATE TABLE IF NOT EXISTS "userlocation" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "address" TEXT NOT NULL,
    "city" VARCHAR(100) NOT NULL,
    "postal_code" VARCHAR(20) NOT NULL,
    "country" VARCHAR(50) NOT NULL,
    "latitude" DOUBLE PRECISION NOT NULL,
    "longitude" DOUBLE PRECISION NOT NULL,
    "is_primary" BOOL NOT NULL  DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "userlocation" IS 'Stocke les adresses associées à un utilisateur (livraison, facturation...).';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)
