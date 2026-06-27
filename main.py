"""
Bright Mind — Entry Point
Runs both User Bot and Admin Bot concurrently.
"""
import asyncio
import logging
import os
import sys

# Load .env if exists (local dev)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def validate_env():
    """Crash early with a clear message if required env vars are missing."""
    required = {
        "TELEGRAM_USER_TOKEN":  os.getenv("TELEGRAM_USER_TOKEN",  ""),
        "TELEGRAM_ADMIN_TOKEN": os.getenv("TELEGRAM_ADMIN_TOKEN", ""),
        "MONGO_URI":            os.getenv("MONGO_URI",            ""),
    }
    missing = [k for k, v in required.items() if not v.strip()]
    if missing:
        logger.error("❌ Missing required environment variables: %s", ", ".join(missing))
        logger.error("Set them in Railway → Variables tab.")
        sys.exit(1)
    logger.info("✅ All required environment variables found.")


async def run_both():
    from bots.user_bot  import build_user_app
    from bots.admin_bot import build_admin_app

    user_app  = build_user_app()
    admin_app = build_admin_app()

    await user_app.initialize()
    await admin_app.initialize()

    await user_app.start()
    await admin_app.start()

    logger.info("✅ User Bot  started  (Labour Workers)")
    logger.info("✅ Admin Bot started  (Managers / HR)")

    async with (
        user_app.updater,
        admin_app.updater,
    ):
        await user_app.updater.start_polling(drop_pending_updates=True)
        await admin_app.updater.start_polling(drop_pending_updates=True)

        logger.info("🤖 Both bots are running.")
        await asyncio.Event().wait()

    await user_app.stop()
    await admin_app.stop()


if __name__ == "__main__":
    validate_env()
    try:
        asyncio.run(run_both())
    except KeyboardInterrupt:
        logger.info("Shutting down…")
