import os
import json
from tinydb import TinyDB, Query
from tinydb.operations import set
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("job_database")

class JobDatabase:
    def __init__(self, db_path="jobs_database.json"):
        """
        Initialize the job database
        
        Args:
            db_path (str): Path to the database file
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
        
        self.db = TinyDB(db_path)
        self.jobs_table = self.db.table('jobs')
        self.Job = Query()
        
        logger.info(f"Initialized job database at {db_path}")
    
    def add_job(self, job):
        """
        Add a job to the database if it doesn't already exist
        
        Args:
            job (dict): Job data to add
            
        Returns:
            bool: True if job was added, False if it already exists
        """
        job_id = job.get('job_id')
        
        if not job_id:
            logger.warning("Cannot add job without job_id")
            return False
            
        # Check if job already exists
        existing_job = self.jobs_table.get(self.Job.job_id == job_id)
        
        if existing_job:
            logger.debug(f"Job {job_id} already exists in database")
            return False
        
        # Add job to database with additional metadata
        job['added_timestamp'] = datetime.now().isoformat()
        job['notified'] = False
        
        self.jobs_table.insert(job)
        logger.info(f"Added job {job_id} to database")
        
        return True
    
    def add_jobs(self, jobs):
        """
        Add multiple jobs to the database, return only new ones
        
        Args:
            jobs (list): List of job dictionaries to add
            
        Returns:
            list: List of newly added job dictionaries
        """
        new_jobs = []
        
        for job in jobs:
            if self.add_job(job):
                new_jobs.append(job)
        
        logger.info(f"Added {len(new_jobs)} new jobs out of {len(jobs)} total")
        return new_jobs
    
    def mark_as_notified(self, job_id):
        """
        Mark a job as notified
        
        Args:
            job_id (str): ID of the job to mark
            
        Returns:
            bool: True if successful, False otherwise
        """
        result = self.jobs_table.update(
            set('notified', True),
            self.Job.job_id == job_id
        )
        
        if result:
            logger.info(f"Marked job {job_id} as notified")
            return True
        else:
            logger.warning(f"Failed to mark job {job_id} as notified - not found")
            return False
    
    def mark_jobs_as_notified(self, job_ids):
        """
        Mark multiple jobs as notified
        
        Args:
            job_ids (list): List of job IDs to mark
            
        Returns:
            int: Number of jobs successfully marked
        """
        count = 0
        for job_id in job_ids:
            if self.mark_as_notified(job_id):
                count += 1
        
        logger.info(f"Marked {count} jobs as notified")
        return count
    
    def get_unnotified_jobs(self):
        """
        Get all jobs that haven't been notified yet
        
        Returns:
            list: List of unnotified job dictionaries
        """
        unnotified_jobs = self.jobs_table.search(self.Job.notified == False)
        logger.info(f"Found {len(unnotified_jobs)} unnotified jobs")
        return unnotified_jobs
    
    def get_all_jobs(self):
        """
        Get all jobs in the database
        
        Returns:
            list: List of all job dictionaries
        """
        all_jobs = self.jobs_table.all()
        logger.info(f"Retrieved {len(all_jobs)} jobs from database")
        return all_jobs 