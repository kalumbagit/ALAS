from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" UUID NOT NULL PRIMARY KEY,
    "email" VARCHAR(254) NOT NULL UNIQUE,
    "phone" VARCHAR(15) NOT NULL UNIQUE,
    "password_hash" VARCHAR(128) NOT NULL,
    "first_name" VARCHAR(30) NOT NULL,
    "last_name" VARCHAR(30) NOT NULL,
    "user_type" VARCHAR(9) NOT NULL DEFAULT 'customer',
    "avatar_url" VARCHAR(255),
    "is_verified" BOOL NOT NULL DEFAULT False,
    "is_active" BOOL NOT NULL DEFAULT True,
    "rating" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "total_ratings" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "user"."user_type" IS 'CUSTOMER: customer\nDELIVERER: deliverer\nMERCHANT: merchant\nADMIN: admin';
COMMENT ON TABLE "user" IS 'Représente un utilisateur de la plateforme (client, livreur, marchand, admin).';
CREATE TABLE IF NOT EXISTS "delivererdetails" (
    "id" UUID NOT NULL PRIMARY KEY,
    "is_online" BOOL NOT NULL DEFAULT False,
    "is_active" BOOL NOT NULL DEFAULT True,
    "is_suspended" BOOL NOT NULL DEFAULT False,
    "suspension_end" TIMESTAMPTZ,
    "suspension_reason" TEXT,
    "total_earnings" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "referral_earnings" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "completed_deliveries" INT NOT NULL DEFAULT 0,
    "identity_type" VARCHAR(14) NOT NULL DEFAULT 'other',
    "identity_document_url" VARCHAR(255),
    "selfie_photo_url" VARCHAR(255),
    "identity_code" VARCHAR(100),
    "identity_verified" BOOL NOT NULL DEFAULT False,
    "verification_method" VARCHAR(12) NOT NULL DEFAULT 'manual',
    "verified_by" VARCHAR(100),
    "verification_date" TIMESTAMPTZ,
    "vehicle_type" VARCHAR(10) NOT NULL DEFAULT 'walking',
    "current_latitude" DECIMAL(9,6),
    "current_longitude" DECIMAL(9,6),
    "referral_code" VARCHAR(20) UNIQUE,
    "total_referrals" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "sponsor_id" UUID REFERENCES "delivererdetails" ("id") ON DELETE SET NULL,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "delivererdetails"."identity_type" IS 'CNI: cni\nPASSPORT: passport\nDRIVER_LICENSE: driver_license\nELECTORAL_CARD: electoral_card\nOTHER: other';
COMMENT ON COLUMN "delivererdetails"."verification_method" IS 'MANUAL: manual\nSELFIE_MATCH: selfie_match\nOTP_ONLY: otp_only\nSPONSORED: sponsored';
COMMENT ON COLUMN "delivererdetails"."vehicle_type" IS 'BIKE: bike\nMOTORCYCLE: motorcycle\nCAR: car\nWALKING: walking\nSCOOTER: scooter';
COMMENT ON TABLE "delivererdetails" IS 'Contient les informations supplémentaires relatives à un livreur.';
CREATE TABLE IF NOT EXISTS "delivererearnings" (
    "id" UUID NOT NULL PRIMARY KEY,
    "amount" DECIMAL(10,2) NOT NULL,
    "is_advance_payment" BOOL NOT NULL DEFAULT False,
    "description" TEXT,
    "status" VARCHAR(20) NOT NULL DEFAULT 'pending',
    "payment_date" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deliverer_id" UUID NOT NULL REFERENCES "delivererdetails" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "delivererearnings"."is_advance_payment" IS 'True si payé à l''avance';
COMMENT ON COLUMN "delivererearnings"."description" IS 'Motif ou détail du paiement';
COMMENT ON COLUMN "delivererearnings"."status" IS 'Statut du paiement';
COMMENT ON TABLE "delivererearnings" IS 'Représente les gains du livreur, incluant les paiements anticipés,';
CREATE TABLE IF NOT EXISTS "merchant" (
    "id" UUID NOT NULL PRIMARY KEY,
    "business_name" VARCHAR(100) NOT NULL,
    "business_type" VARCHAR(11) NOT NULL DEFAULT 'other',
    "description" TEXT,
    "logo_url" VARCHAR(255),
    "banner_url" VARCHAR(255),
    "siret" VARCHAR(50) NOT NULL UNIQUE,
    "is_approved" BOOL NOT NULL DEFAULT False,
    "is_verified" BOOL NOT NULL DEFAULT False,
    "rating" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "total_ratings" INT NOT NULL DEFAULT 0,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "merchant"."business_type" IS 'RESTAURANT: restaurant\nGROCERY: grocery\nPHARMACY: pharmacy\nELECTRONICS: electronics\nFASHION: fashion\nOTHER: other';
COMMENT ON TABLE "merchant" IS 'Représente un marchand enregistré dans la plateforme.';
CREATE TABLE IF NOT EXISTS "userlocation" (
    "id" UUID NOT NULL PRIMARY KEY,
    "address" TEXT NOT NULL,
    "city" VARCHAR(100) NOT NULL,
    "postal_code" VARCHAR(20) NOT NULL,
    "country" VARCHAR(50) NOT NULL,
    "latitude" DOUBLE PRECISION NOT NULL,
    "longitude" DOUBLE PRECISION NOT NULL,
    "is_primary" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
    "eJztXW1z2rgW/isevtx0hpsJNOmmzJ2dIeC2bAFngHS3u+x4FFsBTWzJK9lpmZ3+9yvJNv"
    "g9mLdA6i9tIulI8nP0dp5zpPxbs4kJLXbehRZ6ghTSLnQBslitpfxbw8CG/IfcMnWlBhxn"
    "VUIkuODekkJmWNqMlL5nLgWGy/MfgMVgXRRjBkWOiwgWUh2CXQSxq1iQKQg/EGoDkccU5j"
    "mONfUuLuB7mxcAiPISFFo8+4n/JHMuFA8rvFkKPXouGjSJwVtEeLaHuj2M/vGg7pIZdOeQ"
    "8hb++psnI2zC75CFvzqP+gOClhkDFJmiApmuuwtHpt3d9bofZEnR73vdIJZn41VpZ+HOCV"
    "4W9zxkngsZkTeDGFLgQjMCLPYsK9BFmOT3mCe41IPLrpqrBBM+AM8S6qn978HDhkBHkS2J"
    "fy5/raUUJlpJ4BwkGRxYrmyEXTmYfvhftfpmf4hJvXxqj87evnsjv5Iwd0ZlpkSk9kMKAh"
    "f4ohLXCJBMJ9hCGKbxvCHEggDnQBqVSyB7zwU3ATVMWKG6GuMhrNmjfhcg3mhaX/TaZuwf"
    "Syb0JuJ3wuebPyGHd4MbdXTWkDjzQsiVyb3hRIIcA5XPUT7yy4O6kjsgqMvBe9yYMo85kH"
    "9Gxtx/DtaYaDVc49D64DDeN51jlAa3y0FxkQ2z0U1LJ/A1A/Hz8Ic1wA5GZCmsQ1R3DvWk"
    "N1DHk/bgNoZ3tz1RRU5Tpi4SqWf+arzSxrIS5ffe5JMiflX+1IZqcs1elpv8WRN9Ap5LdE"
    "y+6cCMfnaYHCblKZRCwDgQKZ1O4Hf3WX2uhBMq5cCdnBLVPyYx/Q2/tEdy4xy0/3gT02Ff"
    "G34Mi0emU6ev3SRmjktcYOkQUMx7xdIof7AIyIE5LZrA+EHI7mtduji/2AvKXe3upq8qty"
    "O10xv3tGF8bsjM+Go0Utv9BKgUPkBKN8U1U7qC1ofWILZjQf69emBcIJiBbg/nYJsnnoCX"
    "f8zewN0cWt4f/t9/m43LXy6v3767vOZFZEeWKb8UoJ9xIDG5oYPchf/ZKRA7c0BV7NkSyR"
    "7vCcAGzLBMEpVstNBuBGWtF7Q94W2da5NP6ihtndQ6w15LMTCa4tv2eHyrjSYtxQGMOYS6"
    "U9wd9b6oI73f66jDsdpSTCpGhW4hg+8gcIrVvtqZaKN2X++0R92WAi1ouETMTgNQc4plqy"
    "2FSPNvPS3a4LtuQTxz5/zXxmWBysL1vXGZ2IrDlb8ps3K0yrviCVNW96iVrd08WzOnghPZ"
    "QuMAN6+u1kCYl8qFWOYlzpvQ4rXpzpzwM0xJeLNkK2RTo9cgZs6a9MyoDQVPEtPGxcU668"
    "HFRf6CIPJyMBX7Ha+3tPWZJV+ZoHGQfWwMySbqNuTgZMC83paaU9UBN9YvkR4MZAfOB+3h"
    "Xbufsb/6GS3FBtgD1hSP1f6HnqoP2pPOp5YSrHY2cI252C1vdW3Y/yo2TEfQbwte/lYbjr"
    "WRyjdXvidjRqg/wEpPneY6M6eZP3GayXkTDnf9flFmJUqIVetQ5hQRVEpZoiazgoqreWGu"
    "5gnOEW92KysiWcdB1zrZtLQhfm/3P/eGHzNWuZveZ24d3KNHbhMMNG4RdL52+jzF5qc4ai"
    "x4BVPMLQRuaQA6xUE9LeUbsB75OOCrXEfTJsJSYAYh7oa2wnpzsmBKJmek4VEqDvjCy+V6"
    "WQeuLjSQDawcazpDPDkdffnzoJ5Tm4xdtdMbtPtn7+vvEieAEO/LfFAJnm2FalS+gnVJi5"
    "W1DFKCO9mRn/ef7tTWWmfqN/OnfjMFp8/ehtiU4dAyJH9K+sygUHyc7hOxZc4xcckdHGA2"
    "gnLL8cm/wdT4CT4Y+idyoglmaeGBxnPMDRUbl6wU+6KKDTofYe1881IvF3oTl9oiBOeodu"
    "BnA24i04HBsphFRHYZs3TMiIlAr4fHzAilYARlOAEJhWiGP8NFyjpKwFYQfneso26VuuoF"
    "Bd+WoXCJiSUseihccyJrrE6U4V2/X0sNxB2AeBdUs/uIucPgFplcMdA67XGn3VVrcijeA+"
    "PxG6CmnjMmCw5+N4Hoh88jGf6YGT/xGgZkbHDlu+o3wkONVHe0y1waETF0SJNEhkxsMKWz"
    "7KadTAEYzGSvRduipVxsigKMowCuEWEcVd/zIcYj6FA/1pdxSxvKaOAZx4EpphcG+NYVhA"
    "3LA0GwsAMQFM5QpvAUZCAnkK8nmZydVj7FIvueYI8pUJRV+Ormeq6oym/kemZJ0Soe+Uji"
    "kYFNPJxlORRxPiuhrYme4zo1hUxP46LeXJvqEVHE5pPYxXUHLMToLuuxzKzgxV2WtQkf0w"
    "pDfL4v/Bke3iuw/gOelsT4kXg0o31PwZ8ffZkQe1n3V21AXPSgEE8xfcDFKUUsnuGKuzXg"
    "e4nKlIt8xlGkIKpkKXFA14kISBewpWEfL3epckDvm/UMVoONvI9J2YreqXi7SrEH4O2Wh/"
    "ySLFRSrqKiVpC8DBl1RKZuPcGqJAdLWWpln5bzAFJjDmTXUwbzMq9eZCfb0VKlzWMPKzaQ"
    "FZgKxBTOEK8hOMCagBu2FlAci6td3KeF6Vu3O6ivsmwPs3bUCyzbe48hDBnTZUKJw2lK8H"
    "Bn1KMPiltis034VKqSAxoBN0HbhZcwRuIIcDdqDycthQ84F3iUr0ZT/HGkddTR15Yyo8SA"
    "dDHFtxyoQbvDkxz+6TYwFsEljJE27HXGwQ0MSjAy2BR/aI8/9bSh6Bib87Z2cCGjsY6OG/"
    "kqbiQ1/Brs6J0ENu7DUrbIrPQNjKjMicB6gJsX9wDzjy6LZVyqQnPJ4CAKM8zQAgInFNjN"
    "0n3Y8LSrdTbGq/x98SqTAnYcSp42eSshKvnipO+R3VPh8Gx6DYhVF4AKgOUfHXChCbu64K"
    "b3UqS63h2LSpW4bBCTupL7KSNSq1d7dj+tqyjfV0EqV96CV6rYlLegClfd0kdQhVluG2a5"
    "T1+AhDXDDxDCne8DCPW6Ef/vuchCjKvRo4oJ4wS9cmZY4lHN+iq6LaT36wowbYTfrOUT2E"
    "UblZ/gMOtHvcBPAG2ASpFIS4FT5D6aV+s84cNLFdBHqUd8HA5DKRfLUuAUIWysQ8A18vm3"
    "Rop+Ew88fSN8rZ0DNi+FY1LwRF1Vzeu1XsO4LngO4zoJ6gOizC3t/ItLnSacb9fhN9/m85"
    "tvU/ymBTaAMiZUIRk572/jPI1VcEDHqTixSadp52480QbZj9cFWS3F8JhLbEinuKv2xZt1"
    "InEZtDLFvBBHSPhXw1iPKW53B71hyz8ebeILfb+Grt7nqup9UlPgiZ8YSnuY4lKVh6ki8v"
    "fvIalY1B1jWjlHKudI9VxHxfdWRH6l2CIiP0VLr3OXfRW6Hfk7Q4mNe7932o8orj02NaJh"
    "35sDEg0xP1EgLOK/Grnl0BAmWz+o6sTQ2LdPYglLjm8iCluxj8KKlnzWVzF2ifHoX7IHJl"
    "97mPiBMWIg37sQ+9tdUQ/DmXAkAMQIrvO6DdejstXz8/MMb8XeWqn8FTs6YG9zY9+UKk2j"
    "mR+cHRE5FR7u0JHZBnJLPZsclj8VPA9wN0SM4w0evEyInSagu7/7bYgnNmi5MbkSOU0Udx"
    "+Ynf9UcAGXU/BA8F7ZnL2tmLugcwreBy6CsuBV4J8XS8R0hyIbZE3v50jbiGBFhVec2Suk"
    "VirO7JUqtgp+fWXBry9HENVPI/y1DSky5rUMkinIqRfRS2BV5jliKR/QHVM2uW67zDmZ4a"
    "sLtPei4Xw78dXlMzRPkLLM6/OFf4WJZXO5J2K67SVoREyNEiAGxU8TwL1QMrxFN/M9yt/G"
    "2jCPRFiKJIC8w/wD/zKRIcPamfv3ccJagKL46mLmMEkSJnZkUcFN1pZ8yO3lx/8B4FsGOA"
    "=="
)
