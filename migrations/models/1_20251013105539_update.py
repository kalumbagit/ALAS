from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "delivererdetails" ALTER COLUMN "identity_type" TYPE VARCHAR(18) USING "identity_type"::VARCHAR(18);
        COMMENT ON COLUMN "delivererdetails"."identity_type" IS 'CNI: cni
PASSPORT: passport
DRIVER_LICENSE: driver_license
ELECTORAL_CARD: electoral_card
CNI_RECEIPT: recépicé de la cni
OTHER: other';
        ALTER TABLE "delivererearnings" ALTER COLUMN "status" SET DEFAULT 'EarningStatus.PENDING';
        ALTER TABLE "delivererearnings" ALTER COLUMN "status" TYPE VARCHAR(10) USING "status"::VARCHAR(10);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        COMMENT ON COLUMN "delivererdetails"."identity_type" IS 'CNI: cni
PASSPORT: passport
DRIVER_LICENSE: driver_license
ELECTORAL_CARD: electoral_card
OTHER: other';
        ALTER TABLE "delivererdetails" ALTER COLUMN "identity_type" TYPE VARCHAR(14) USING "identity_type"::VARCHAR(14);
        ALTER TABLE "delivererearnings" ALTER COLUMN "status" TYPE VARCHAR(20) USING "status"::VARCHAR(20);
        ALTER TABLE "delivererearnings" ALTER COLUMN "status" SET DEFAULT 'pending';"""


MODELS_STATE = (
    "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"
)
