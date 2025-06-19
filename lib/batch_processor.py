#!/usr/bin/env python3
"""
Batch Processor - Handles batch processing for Anthropic and OpenAI APIs
"""

import os
import json
import time
import tempfile
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import requests
from dataclasses import dataclass

from ai_client import AIClient
from logger import get_logger


@dataclass
class BatchRequest:
    """Represents a single request in a batch"""
    id: str
    directive_path: Path
    platform: str
    model: str
    prompt: str
    metadata: Dict[str, Any]


@dataclass
class BatchJob:
    """Represents a batch job submitted to an API"""
    id: str
    platform: str
    model: str
    requests: List[BatchRequest]
    api_batch_id: Optional[str] = None
    status: str = "pending"  # pending, submitted, processing, completed, failed
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BatchProcessor:
    """Handles batch processing for multiple AI platforms"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.logger = get_logger("batch_processor", base_path)
        self.ai_client = AIClient()
        
        # Batch configuration
        self.max_anthropic_batch_size = 10000  # Max 10,000 requests per batch
        self.max_openai_batch_size = 50000     # OpenAI has higher limits
        self.max_batch_size_mb = 32            # Max 32MB per batch
        self.batch_timeout_hours = 24          # Max 24 hours for batch processing
        
        # Batch storage
        self.batch_dir = self.base_path / "directives" / "batches"
        self.batch_dir.mkdir(exist_ok=True)
        
        # Active batch jobs
        self.active_batches: Dict[str, BatchJob] = {}
        
    def group_requests_for_batching(self, requests: List[BatchRequest]) -> List[List[BatchRequest]]:
        """Group requests into optimal batches by platform and model"""
        # Group by platform and model
        groups = {}
        for request in requests:
            key = f"{request.platform}_{request.model}"
            if key not in groups:
                groups[key] = []
            groups[key].append(request)
        
        # Split large groups into smaller batches
        batches = []
        for key, group in groups.items():
            platform = group[0].platform
            max_size = (self.max_anthropic_batch_size if platform == 'claude' 
                       else self.max_openai_batch_size)
            
            # Split into chunks
            for i in range(0, len(group), max_size):
                batch = group[i:i + max_size]
                batches.append(batch)
        
        return batches
    
    def create_batch_job(self, requests: List[BatchRequest]) -> BatchJob:
        """Create a new batch job"""
        if not requests:
            raise ValueError("Cannot create batch job with no requests")
        
        # All requests should have same platform and model
        platform = requests[0].platform
        model = requests[0].model
        
        # Verify all requests are compatible
        for req in requests:
            if req.platform != platform or req.model != model:
                raise ValueError("All requests in a batch must use same platform and model")
        
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        
        return BatchJob(
            id=batch_id,
            platform=platform,
            model=model,
            requests=requests
        )
    
    def submit_anthropic_batch(self, batch_job: BatchJob) -> bool:
        """Submit a batch job to Anthropic's Message Batches API"""
        if not self.ai_client.claude_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        # Create batch requests in Anthropic format
        batch_requests = []
        for req in batch_job.requests:
            batch_requests.append({
                "custom_id": req.id,
                "params": {
                    "model": req.model,
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": req.prompt}]
                }
            })
        
        # Submit to Anthropic Batch API
        url = "https://api.anthropic.com/v1/message_batches"
        headers = {
            "x-api-key": self.ai_client.claude_key,
            "anthropic-version": "2023-06-01", 
            "content-type": "application/json"
        }
        
        data = {
            "requests": batch_requests
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            batch_job.api_batch_id = result["id"]
            batch_job.status = "submitted"
            batch_job.submitted_at = datetime.now()
            
            self.logger.info(f"Submitted Anthropic batch {batch_job.id} with {len(batch_job.requests)} requests")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to submit Anthropic batch {batch_job.id}: {e}")
            batch_job.status = "failed"
            batch_job.error = str(e)
            return False
    
    def submit_openai_batch(self, batch_job: BatchJob) -> bool:
        """Submit a batch job to OpenAI's Batch API"""
        if not self.ai_client.openai_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        # Create JSONL file for OpenAI batch
        batch_file_path = self.batch_dir / f"{batch_job.id}.jsonl"
        
        try:
            with open(batch_file_path, 'w') as f:
                for req in batch_job.requests:
                    batch_line = {
                        "custom_id": req.id,
                        "method": "POST",
                        "url": "/v1/chat/completions",
                        "body": {
                            "model": req.model,
                            "messages": [{"role": "user", "content": req.prompt}],
                            "max_tokens": 4000
                        }
                    }
                    f.write(json.dumps(batch_line) + '\n')
            
            # Upload batch file to OpenAI
            files_url = "https://api.openai.com/v1/files"
            files_headers = {
                "Authorization": f"Bearer {self.ai_client.openai_key}"
            }
            
            with open(batch_file_path, 'rb') as f:
                files_data = {
                    "purpose": "batch"
                }
                files_response = requests.post(
                    files_url, 
                    headers=files_headers, 
                    data=files_data,
                    files={"file": f}
                )
                files_response.raise_for_status()
                file_result = files_response.json()
                file_id = file_result["id"]
            
            # Create batch job
            batch_url = "https://api.openai.com/v1/batches"
            batch_headers = {
                "Authorization": f"Bearer {self.ai_client.openai_key}",
                "Content-Type": "application/json"
            }
            
            batch_data = {
                "input_file_id": file_id,
                "endpoint": "/v1/chat/completions",
                "completion_window": "24h"
            }
            
            batch_response = requests.post(batch_url, headers=batch_headers, json=batch_data)
            batch_response.raise_for_status()
            
            result = batch_response.json()
            batch_job.api_batch_id = result["id"]
            batch_job.status = "submitted"
            batch_job.submitted_at = datetime.now()
            
            self.logger.info(f"Submitted OpenAI batch {batch_job.id} with {len(batch_job.requests)} requests")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to submit OpenAI batch {batch_job.id}: {e}")
            batch_job.status = "failed"
            batch_job.error = str(e)
            return False
        finally:
            # Clean up batch file
            if batch_file_path.exists():
                batch_file_path.unlink()
    
    def submit_batch_job(self, batch_job: BatchJob) -> bool:
        """Submit a batch job to the appropriate API"""
        if batch_job.platform == "claude":
            return self.submit_anthropic_batch(batch_job)
        elif batch_job.platform == "openai":
            return self.submit_openai_batch(batch_job)
        else:
            raise ValueError(f"Unsupported platform: {batch_job.platform}")
    
    def check_anthropic_batch_status(self, batch_job: BatchJob) -> bool:
        """Check status of an Anthropic batch job"""
        if not batch_job.api_batch_id:
            return False
        
        url = f"https://api.anthropic.com/v1/message_batches/{batch_job.api_batch_id}"
        headers = {
            "x-api-key": self.ai_client.claude_key,
            "anthropic-version": "2023-06-01"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            api_status = result.get("processing_status", "unknown")
            
            if api_status == "completed":
                batch_job.status = "completed"
                batch_job.completed_at = datetime.now()
                batch_job.results = result
                return True
            elif api_status in ["failed", "expired", "canceled"]:
                batch_job.status = "failed"
                batch_job.error = f"Batch {api_status}"
                return True
            else:
                batch_job.status = "processing"
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to check Anthropic batch status: {e}")
            return False
    
    def check_openai_batch_status(self, batch_job: BatchJob) -> bool:
        """Check status of an OpenAI batch job"""
        if not batch_job.api_batch_id:
            return False
        
        url = f"https://api.openai.com/v1/batches/{batch_job.api_batch_id}"
        headers = {
            "Authorization": f"Bearer {self.ai_client.openai_key}"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            api_status = result.get("status", "unknown")
            
            if api_status == "completed":
                batch_job.status = "completed"
                batch_job.completed_at = datetime.now()
                batch_job.results = result
                return True
            elif api_status in ["failed", "expired", "cancelled"]:
                batch_job.status = "failed"
                batch_job.error = f"Batch {api_status}"
                return True
            else:
                batch_job.status = "processing"
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to check OpenAI batch status: {e}")
            return False
    
    def check_batch_status(self, batch_job: BatchJob) -> bool:
        """Check status of a batch job"""
        if batch_job.platform == "claude":
            return self.check_anthropic_batch_status(batch_job)
        elif batch_job.platform == "openai":
            return self.check_openai_batch_status(batch_job)
        else:
            raise ValueError(f"Unsupported platform: {batch_job.platform}")
    
    def process_batch_results(self, batch_job: BatchJob) -> Dict[str, Dict[str, Any]]:
        """Process and extract results from a completed batch job"""
        if batch_job.status != "completed" or not batch_job.results:
            return {}
        
        results = {}
        
        if batch_job.platform == "claude":
            # Process Anthropic batch results
            if "results" in batch_job.results:
                for result in batch_job.results["results"]:
                    custom_id = result.get("custom_id")
                    if result.get("result", {}).get("type") == "message":
                        content = result["result"]["content"][0]["text"]
                        results[custom_id] = {
                            "success": True,
                            "content": content,
                            "platform": "claude",
                            "model": batch_job.model
                        }
                    else:
                        results[custom_id] = {
                            "success": False,
                            "error": result.get("error", {}).get("message", "Unknown error"),
                            "platform": "claude",
                            "model": batch_job.model
                        }
        
        elif batch_job.platform == "openai":
            # Process OpenAI batch results
            if "output_file_id" in batch_job.results:
                # Download results file
                file_id = batch_job.results["output_file_id"]
                file_url = f"https://api.openai.com/v1/files/{file_id}/content"
                headers = {"Authorization": f"Bearer {self.ai_client.openai_key}"}
                
                try:
                    response = requests.get(file_url, headers=headers)
                    response.raise_for_status()
                    
                    # Parse JSONL results
                    for line in response.text.strip().split('\n'):
                        if line:
                            result = json.loads(line)
                            custom_id = result.get("custom_id")
                            
                            if result.get("response", {}).get("status_code") == 200:
                                content = result["response"]["body"]["choices"][0]["message"]["content"]
                                results[custom_id] = {
                                    "success": True,
                                    "content": content,
                                    "platform": "openai",
                                    "model": batch_job.model
                                }
                            else:
                                error_msg = result.get("error", {}).get("message", "Unknown error")
                                results[custom_id] = {
                                    "success": False,
                                    "error": error_msg,
                                    "platform": "openai",
                                    "model": batch_job.model
                                }
                                
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Failed to download OpenAI batch results: {e}")
        
        return results
    
    def wait_for_batch_completion(self, batch_jobs: List[BatchJob], 
                                 max_wait_hours: int = 24, 
                                 poll_interval: int = 30) -> List[BatchJob]:
        """Wait for batch jobs to complete with polling"""
        start_time = datetime.now()
        max_wait = timedelta(hours=max_wait_hours)
        
        completed_jobs = []
        
        while batch_jobs and (datetime.now() - start_time) < max_wait:
            remaining_jobs = []
            
            for batch_job in batch_jobs:
                if self.check_batch_status(batch_job):
                    # Job completed (success or failure)
                    completed_jobs.append(batch_job)
                    self.logger.info(f"Batch {batch_job.id} completed with status: {batch_job.status}")
                else:
                    # Job still processing
                    remaining_jobs.append(batch_job)
            
            batch_jobs = remaining_jobs
            
            if batch_jobs:
                self.logger.info(f"Waiting for {len(batch_jobs)} batch jobs to complete...")
                time.sleep(poll_interval)
        
        # Handle any jobs that didn't complete in time
        for batch_job in batch_jobs:
            batch_job.status = "timeout"
            batch_job.error = f"Batch did not complete within {max_wait_hours} hours"
            completed_jobs.append(batch_job)
        
        return completed_jobs
    
    def process_directives_in_batches(self, requests: List[BatchRequest]) -> Dict[str, Dict[str, Any]]:
        """Process multiple directives using batch APIs"""
        if not requests:
            return {}
        
        self.logger.info(f"Processing {len(requests)} directives in batches...")
        
        # Group requests into batches
        batches = self.group_requests_for_batching(requests)
        self.logger.info(f"Created {len(batches)} batch jobs")
        
        # Create and submit batch jobs
        batch_jobs = []
        for batch_requests in batches:
            batch_job = self.create_batch_job(batch_requests)
            if self.submit_batch_job(batch_job):
                batch_jobs.append(batch_job)
                self.active_batches[batch_job.id] = batch_job
            else:
                self.logger.error(f"Failed to submit batch job {batch_job.id}")
        
        if not batch_jobs:
            self.logger.error("No batch jobs were successfully submitted")
            return {}
        
        # Wait for completion
        completed_jobs = self.wait_for_batch_completion(batch_jobs)
        
        # Process results
        all_results = {}
        for batch_job in completed_jobs:
            if batch_job.status == "completed":
                results = self.process_batch_results(batch_job)
                all_results.update(results)
            else:
                self.logger.error(f"Batch {batch_job.id} failed: {batch_job.error}")
        
        return all_results