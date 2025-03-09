import os
import subprocess
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_backup():
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        backup_file = f"{backup_dir}/backup_{timestamp}.sql"
        
        # Get PostgreSQL connection details from environment
        db_name = os.environ.get('PGDATABASE')
        db_user = os.environ.get('PGUSER')
        db_host = os.environ.get('PGHOST')
        db_port = os.environ.get('PGPORT')
        
        # Create backup using pg_dump
        cmd = [
            'pg_dump',
            f'--dbname=postgresql://{db_user}:@{db_host}:{db_port}/{db_name}',
            '--format=p',
            f'--file={backup_file}'
        ]
        
        subprocess.run(cmd, check=True)
        logger.info(f"Database backup created successfully: {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Backup creation failed: {str(e)}")
        raise
