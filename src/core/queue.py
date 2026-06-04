import asyncio
from datetime import datetime
from src.core.logger import setup_logger
from src.database.session import db_session
from src.database.models import GenerationJob, JobStatus

logger = setup_logger("queue_manager")

class QueueManager:
    def __init__(self, bot):
        self.bot = bot
        self.queue = []  # List of dicts representing queued jobs
        self.active_job = None  # Dict of the currently running job
        self.lock = asyncio.Lock()
        self.cleanup_task = None

    def start(self):
        """Starts any background loops needed by the queue manager (e.g. timeout cleanup)."""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._stuck_job_monitor())

    async def add_job(self, job_id, payload, client_id, channel, message_id, workflow_name):
        job_data = {
            "job_id": job_id,
            "payload": payload,
            "client_id": client_id,
            "channel": channel,
            "message_id": message_id,
            "workflow_name": workflow_name,
            "prompt_id": None,
            "queued_at": datetime.utcnow(),
            "started_at": None
        }
        
        async with self.lock:
            # Check if this job is already in queue
            if any(j["job_id"] == job_id for j in self.queue) or (self.active_job and self.active_job["job_id"] == job_id):
                logger.info(f"Job {job_id} is already in the queue or executing.")
                return

            self.queue.append(job_data)
            position = len(self.queue)
            
            if not self.active_job:
                logger.info(f"Queue is empty. Starting job {job_id} immediately.")
                asyncio.create_task(self.process_next())
            else:
                logger.info(f"Job {job_id} added to queue at position {position}.")
                await self.update_discord_message(job_data, position)

    async def process_next(self):
        async with self.lock:
            if self.active_job:
                return
            if not self.queue:
                return
            
            self.active_job = self.queue.pop(0)
            self.active_job["started_at"] = datetime.utcnow()
            
            # Update positions for the rest of the queue
            for i, job in enumerate(self.queue, 1):
                await self.update_discord_message(job, i)
                
        # Start executing the job outside the lock to prevent blocking
        await self.execute_active_job()

    async def execute_active_job(self):
        job_data = self.active_job
        if not job_data:
            return
            
        job_id = job_data["job_id"]
        payload = job_data["payload"]
        client_id = job_data["client_id"]
        channel = job_data["channel"]
        message_id = job_data["message_id"]
        
        logger.info(f"Executing queued job {job_id}")
        
        if channel and message_id:
            try:
                msg = await channel.fetch_message(message_id)
                await msg.edit(content="Please wait while we spin this up...")
            except Exception as e:
                logger.warning(f"Failed to update progress message for job {job_id}: {e}")

        # Queue prompt in ComfyUI
        try:
            prompt_id = await self.bot.api_client.queue_prompt(payload, client_id)
            if prompt_id:
                job_data["prompt_id"] = prompt_id
                with db_session() as db:
                    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
                    if job:
                        job.comfy_prompt_id = prompt_id
                        job.status = JobStatus.PROCESSING
                logger.info(f"Queued prompt {prompt_id} for job {job_id}")
            else:
                raise Exception("ComfyUI did not return a prompt ID.")
        except Exception as e:
            logger.error(f"Failed to queue prompt for job {job_id}: {e}")
            with db_session() as db:
                job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
                if job:
                    job.status = JobStatus.FAILED
                
            if channel and message_id:
                try:
                    msg = await channel.fetch_message(message_id)
                    await msg.edit(content=f"❌ **Generation failed**: Could not queue command to ComfyUI. ({str(e)})")
                except Exception:
                    pass
            
            # Auto-cleanup and move to next
            asyncio.create_task(self.on_job_completed(None))

    async def on_job_completed(self, prompt_id):
        async with self.lock:
            if self.active_job:
                active_prompt_id = self.active_job.get("prompt_id")
                # If prompt_id matches or we do a force cleanup (prompt_id=None or matches job_id)
                if prompt_id is None or active_prompt_id == prompt_id or self.active_job["job_id"] == prompt_id:
                    logger.info(f"Active job {self.active_job['job_id']} marked as finished in queue manager.")
                    self.active_job = None
                    asyncio.create_task(self.process_next())

    async def update_discord_message(self, job_data, position):
        channel = job_data["channel"]
        message_id = job_data["message_id"]
        if not message_id or not channel:
            return
        try:
            msg = await channel.fetch_message(message_id)
            display_name = job_data["workflow_name"]
            # Clear embeds or details from previous stages to show clean queue status
            await msg.edit(content=f"⏳ **Queued**: You are at position **#{position}** in the queue for `{display_name}`. Please wait...")
        except Exception as e:
            logger.warning(f"Failed to update queue position message: {e}")

    async def _stuck_job_monitor(self):
        """Periodically scans the active job and fails it if it has been running for > 15 minutes."""
        while True:
            try:
                await asyncio.sleep(60)
                async with self.lock:
                    if self.active_job and self.active_job["started_at"]:
                        elapsed = (datetime.utcnow() - self.active_job["started_at"]).total_seconds()
                        if elapsed > 900:  # 15 minutes
                            logger.warning(f"Job {self.active_job['job_id']} has been running for {elapsed}s. Timing out...")
                            
                            # Mark as FAILED in database
                            try:
                                with db_session() as db:
                                    job = db.query(GenerationJob).filter(GenerationJob.id == self.active_job["job_id"]).first()
                                    if job and job.status == JobStatus.PROCESSING:
                                        job.status = JobStatus.FAILED
                            except Exception as db_err:
                                logger.error(f"Error marking stuck job as failed in DB: {db_err}")

                            # Edit Discord message
                            channel = self.active_job["channel"]
                            message_id = self.active_job["message_id"]
                            if channel and message_id:
                                try:
                                    msg = await channel.fetch_message(message_id)
                                    await msg.edit(content="❌ **Generation timed out**: The generation took too long to complete. Moving to next in queue.")
                                except Exception:
                                    pass

                            # Force next job
                            self.active_job = None
                            asyncio.create_task(self.process_next())
            except Exception as monitor_err:
                logger.error(f"Error in stuck job monitor loop: {monitor_err}")
