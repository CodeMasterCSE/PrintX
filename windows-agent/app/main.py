import time
import sys
from app.config import agent_settings
from app.logging_config import setup_agent_logging, logger
from app.printer_manager import printer_manager
from app.heartbeat import heartbeat_sender
from app.job_receiver import job_receiver


def main():
    setup_agent_logging()
    logger.info("==================================================")
    logger.info(f" Starting PrintX Windows Agent (ID: {agent_settings.AGENT_ID})")
    logger.info(f" Target Environment: Windows 11 Native")
    logger.info("==================================================")

    # 1. Inspect installed Windows Printers
    printers = printer_manager.get_installed_printers()
    logger.info(f"Detected {len(printers)} installed Windows printer queue(s):")
    for p in printers:
        flag = " [DEFAULT]" if p.is_default else ""
        logger.info(f"  - '{p.name}' | Driver: {p.driver_name} | Port: {p.port_name}{flag}")

    target = printer_manager.resolve_target_printer()
    if target:
        logger.info(f"Active Dispatch Queue: '{target.name}' (Status: {target.status})")
    else:
        logger.warning("No suitable target or fallback printer discovered on this Windows system!")

    last_heartbeat_time = 0
    poll_interval = agent_settings.POLL_INTERVAL_SECONDS
    heartbeat_interval = agent_settings.HEARTBEAT_INTERVAL_SECONDS

    logger.info(f"Agent initialized. Polling interval: {poll_interval}s, Heartbeat: {heartbeat_interval}s")
    logger.info("Listening for authorized print jobs... Press Ctrl+C to terminate.")

    try:
        while True:
            now = time.time()

            # Heartbeat cycle
            if now - last_heartbeat_time >= heartbeat_interval:
                heartbeat_sender.send_heartbeat()
                last_heartbeat_time = now

            # Job polling cycle
            job = job_receiver.poll_next_job()
            if job:
                logger.info(f"Incoming authorized job: {job.get('job_number')} (ID: {job.get('id')})")
                job_receiver.process_submission(job)

            time.sleep(poll_interval)
    except KeyboardInterrupt:
        logger.info("Agent received shutdown signal. Terminating cleanly.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal agent error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

