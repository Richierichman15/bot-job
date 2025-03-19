import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobDatabase:
    def __init__(self, db_file="jobs_database.json"):
        """Initialize the job database"""
        self.db_file = db_file
        self.jobs = self._load_database()
    
    def _load_database(self):
        """Load the job database from file"""
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, 'r') as f:
                    return json.load(f)
            else:
                logger.info(f"Creating new database at {self.db_file}")
                return {}
        except Exception as e:
            logger.error(f"Error loading database: {str(e)}")
            return {}
    
    def _save_database(self):
        """Save the job database to file"""
        try:
            with open(self.db_file, 'w') as f:
                json.dump(self.jobs, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving database: {str(e)}")
            return False
    
    def add_job(self, application):
        """
        Add a job application to the database
        
        Args:
            application (dict): Job application package
            
        Returns:
            bool: Whether the job was added successfully
        """
        try:
            job_id = application['job_data'].get('job_id')
            if not job_id:
                logger.warning("Job ID not found in application")
                return False
            
            if job_id not in self.jobs:
                # Add job with status tracking
                self.jobs[job_id] = {
                    'application': application,
                    'status': 'new',
                    'added_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'notifications_sent': 0,
                    'applied': False,
                    'application_date': None,
                    'follow_up_date': None,
                    'notes': []
                }
                
                logger.info(f"Added job {job_id} to database")
                self._save_database()
                return True
            else:
                logger.debug(f"Job {job_id} already exists in database")
                return False
                
        except Exception as e:
            logger.error(f"Error adding job to database: {str(e)}")
            return False
    
    def update_job_status(self, job_id, status, notes=None):
        """
        Update the status of a job in the database
        
        Args:
            job_id (str): Job ID to update
            status (str): New status ('new', 'notified', 'applied', 'interviewing', 'rejected', 'accepted')
            notes (str): Optional notes about the status change
        """
        try:
            if job_id in self.jobs:
                self.jobs[job_id]['status'] = status
                self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
                
                if status == 'applied':
                    self.jobs[job_id]['applied'] = True
                    self.jobs[job_id]['application_date'] = datetime.now().isoformat()
                
                if notes:
                    self.jobs[job_id]['notes'].append({
                        'timestamp': datetime.now().isoformat(),
                        'note': notes
                    })
                
                self._save_database()
                logger.info(f"Updated job {job_id} status to {status}")
                return True
            else:
                logger.warning(f"Job {job_id} not found in database")
                return False
                
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
            return False
    
    def mark_notification_sent(self, job_id):
        """
        Mark that a notification has been sent for a job
        
        Args:
            job_id (str): Job ID to update
        """
        try:
            if job_id in self.jobs:
                self.jobs[job_id]['notifications_sent'] += 1
                self.jobs[job_id]['status'] = 'notified'
                self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
                self._save_database()
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking notification sent: {str(e)}")
            return False
    
    def get_job(self, job_id):
        """
        Get a job from the database
        
        Args:
            job_id (str): Job ID to retrieve
            
        Returns:
            dict: Job data or None if not found
        """
        return self.jobs.get(job_id)
    
    def job_exists(self, job_id):
        """
        Check if a job exists in the database
        
        Args:
            job_id (str): Job ID to check
            
        Returns:
            bool: Whether the job exists
        """
        return job_id in self.jobs
    
    def get_jobs_by_status(self, status):
        """
        Get all jobs with a particular status
        
        Args:
            status (str): Status to filter by
            
        Returns:
            list: List of jobs with the specified status
        """
        return [
            job for job in self.jobs.values()
            if job['status'] == status
        ]
    
    def get_all_jobs(self):
        """
        Get all jobs in the database
        
        Returns:
            dict: All jobs in the database
        """
        return self.jobs
    
    def add_note(self, job_id, note):
        """
        Add a note to a job
        
        Args:
            job_id (str): Job ID to add note to
            note (str): Note to add
        """
        try:
            if job_id in self.jobs:
                if 'notes' not in self.jobs[job_id]:
                    self.jobs[job_id]['notes'] = []
                
                self.jobs[job_id]['notes'].append({
                    'timestamp': datetime.now().isoformat(),
                    'note': note
                })
                
                self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
                self._save_database()
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding note: {str(e)}")
            return False
    
    def get_stats(self):
        """
        Get statistics about the jobs in the database
        
        Returns:
            dict: Statistics about the jobs
        """
        stats = {
            'total_jobs': len(self.jobs),
            'status_counts': {},
            'applied_count': 0,
            'active_applications': 0,
            'success_rate': 0
        }
        
        for job in self.jobs.values():
            # Count by status
            status = job['status']
            stats['status_counts'][status] = stats['status_counts'].get(status, 0) + 1
            
            # Count applications
            if job['applied']:
                stats['applied_count'] += 1
            
            # Count active applications (applied but no final decision)
            if job['applied'] and status not in ['rejected', 'accepted']:
                stats['active_applications'] += 1
        
        # Calculate success rate (if any applications)
        if stats['applied_count'] > 0:
            accepted = stats['status_counts'].get('accepted', 0)
            stats['success_rate'] = (accepted / stats['applied_count']) * 100
        
        return stats 