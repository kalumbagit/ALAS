from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "revoked_tokens" (
    "id" UUID NOT NULL PRIMARY KEY,
    "jti" VARCHAR(255) NOT NULL UNIQUE,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "revoked_tokens"."jti" IS 'JWT ID unique';
COMMENT ON COLUMN "revoked_tokens"."expires_at" IS 'Date d''expiration du token';
COMMENT ON TABLE "revoked_tokens" IS 'Table des tokens JWT révoqués (denylist)';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "revoked_tokens";"""


MODELS_STATE = (
    "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"
    "tia4ko4Cptv3zIxeHnv/AF75E="
)
