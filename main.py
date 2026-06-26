"""
Bright Mind – Entry Point
Runs both User Bot and Admin Bot concurrently.
"""
import asyncio
import logging
from bots.user_bot  import build_user_app
from bots.admin_bot import build_admin_app

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def run_both():
    user_app  = build_user_app()
    admin_app = build_admin_app()

    await user_app.initialize()
    await admin_app.initialize()

    await user_app.start()
    await admin_app.start()

    logger.info("✅ User Bot  started  (Labour Workers)")
    logger.info("✅ Admin Bot started  (Managers / HR)")

    # Start polling on both bots simultaneously
    async with (
        user_app.updater,
        admin_app.updater,
    ):
        await user_app.updater.start_polling(drop_pending_updates=True)
        await admin_app.updater.start_polling(drop_pending_updates=True)

        logger.info("🤖 Both bots are running. Press Ctrl+C to stop.")
        await asyncio.Event().wait()   # run forever

    await user_app.stop()
    await admin_app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(run_both())
    except KeyboardInterrupt:
        logger.info("Shutting down…")
