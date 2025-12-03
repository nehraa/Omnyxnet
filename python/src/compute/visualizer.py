"""
Result Visualization for Distributed Compute

This module provides utilities for visualizing compute job results,
including progress tracking, result formatting, and basic plotting.
"""

import logging
import json
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class JobSummary:
    """Summary of a compute job."""
    job_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    input_size: int
    output_size: int
    num_chunks: int
    total_time_ms: int
    chunks_per_second: float
    bytes_per_second: float


class ResultVisualizer:
    """Visualizer for compute job results.
    
    This class provides methods for formatting and displaying
    compute job results in various formats.
    
    Example:
        visualizer = ResultVisualizer()
        summary = visualizer.summarize_job(client, job_id)
        print(visualizer.format_summary(summary))
    """
    
    def __init__(self):
        """Initialize the visualizer."""
        self._history: List[JobSummary] = []
    
    def summarize_job(
        self,
        job_id: str,
        status: str,
        input_size: int,
        output_size: int,
        num_chunks: int,
        start_time: datetime,
        end_time: Optional[datetime] = None,
    ) -> JobSummary:
        """Create a summary of a compute job.
        
        Args:
            job_id: The job ID
            status: Job status
            input_size: Input data size in bytes
            output_size: Output data size in bytes
            num_chunks: Number of chunks processed
            start_time: When the job started
            end_time: When the job ended (None if still running)
            
        Returns:
            JobSummary object
        """
        if end_time:
            duration = (end_time - start_time).total_seconds() * 1000
        else:
            duration = 0
        
        chunks_per_second = num_chunks / (duration / 1000) if duration > 0 else 0
        bytes_per_second = input_size / (duration / 1000) if duration > 0 else 0
        
        summary = JobSummary(
            job_id=job_id,
            status=status,
            start_time=start_time,
            end_time=end_time,
            input_size=input_size,
            output_size=output_size,
            num_chunks=num_chunks,
            total_time_ms=int(duration),
            chunks_per_second=chunks_per_second,
            bytes_per_second=bytes_per_second,
        )
        
        self._history.append(summary)
        return summary
    
    def format_summary(self, summary: JobSummary) -> str:
        """Format a job summary as a human-readable string.
        
        Args:
            summary: JobSummary object
            
        Returns:
            Formatted string
        """
        lines = [
            f"Job Summary: {summary.job_id}",
            "=" * 50,
            f"Status:        {summary.status}",
            f"Start Time:    {summary.start_time.isoformat()}",
        ]
        
        if summary.end_time:
            lines.append(f"End Time:      {summary.end_time.isoformat()}")
            lines.append(f"Duration:      {summary.total_time_ms:,} ms")
        
        lines.extend([
            f"Input Size:    {self._format_bytes(summary.input_size)}",
            f"Output Size:   {self._format_bytes(summary.output_size)}",
            f"Chunks:        {summary.num_chunks}",
        ])
        
        if summary.total_time_ms > 0:
            lines.extend([
                f"Throughput:    {self._format_bytes(int(summary.bytes_per_second))}/s",
                f"Chunks/sec:    {summary.chunks_per_second:.2f}",
            ])
        
        return "\n".join(lines)
    
    def format_json(self, summary: JobSummary) -> str:
        """Format a job summary as JSON.
        
        Args:
            summary: JobSummary object
            
        Returns:
            JSON string
        """
        return json.dumps({
            'job_id': summary.job_id,
            'status': summary.status,
            'start_time': summary.start_time.isoformat(),
            'end_time': summary.end_time.isoformat() if summary.end_time else None,
            'input_size': summary.input_size,
            'output_size': summary.output_size,
            'num_chunks': summary.num_chunks,
            'total_time_ms': summary.total_time_ms,
            'chunks_per_second': summary.chunks_per_second,
            'bytes_per_second': summary.bytes_per_second,
        }, indent=2)
    
    def format_progress_bar(
        self,
        progress: float,
        width: int = 40,
        prefix: str = "Progress",
    ) -> str:
        """Format a progress bar.
        
        Args:
            progress: Progress value (0.0 to 1.0)
            width: Width of the progress bar
            prefix: Prefix text
            
        Returns:
            Formatted progress bar string
        """
        filled = int(width * progress)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        percentage = progress * 100
        return f"{prefix}: [{bar}] {percentage:.1f}%"
    
    def format_table(self, summaries: List[JobSummary]) -> str:
        """Format multiple job summaries as a table.
        
        Args:
            summaries: List of JobSummary objects
            
        Returns:
            Formatted table string
        """
        if not summaries:
            return "No jobs to display"
        
        # Headers
        headers = ["Job ID", "Status", "Chunks", "Duration (ms)", "Throughput"]
        
        # Calculate column widths
        widths = [len(h) for h in headers]
        rows = []
        
        for s in summaries:
            row = [
                s.job_id[:16],  # Truncate long IDs
                s.status[:10],
                str(s.num_chunks),
                str(s.total_time_ms),
                f"{self._format_bytes(int(s.bytes_per_second))}/s" if s.bytes_per_second > 0 else "N/A",
            ]
            rows.append(row)
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))
        
        # Format header
        header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
        separator = "-+-".join("-" * w for w in widths)
        
        # Format rows
        row_lines = [
            " | ".join(cell.ljust(w) for cell, w in zip(row, widths))
            for row in rows
        ]
        
        return "\n".join([header_line, separator] + row_lines)
    
    def get_history(self) -> List[JobSummary]:
        """Get the history of job summaries.
        
        Returns:
            List of JobSummary objects
        """
        return self._history.copy()
    
    def clear_history(self):
        """Clear the job history."""
        self._history.clear()
    
    def _format_bytes(self, size: int) -> str:
        """Format bytes as human-readable string.
        
        Args:
            size: Size in bytes
            
        Returns:
            Human-readable size string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(size) < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    def print_result(self, result: bytes, max_display: int = 1000):
        """Print a result with optional truncation.
        
        Args:
            result: Result bytes
            max_display: Maximum bytes to display
        """
        display = result[:max_display]
        
        # Try to decode as text
        try:
            text = display.decode('utf-8')
            print(f"Result ({len(result)} bytes):")
            print("-" * 40)
            print(text)
            if len(result) > max_display:
                print(f"... ({len(result) - max_display} more bytes)")
        except UnicodeDecodeError:
            # Binary data - show hex
            print(f"Result ({len(result)} bytes, binary):")
            print("-" * 40)
            print(display.hex()[:200])
            if len(result) > max_display:
                print(f"... ({len(result) - max_display} more bytes)")


# Convenience functions

def print_progress(current: int, total: int, prefix: str = "Progress"):
    """Print a progress update.
    
    Args:
        current: Current progress value
        total: Total value
        prefix: Prefix text
    """
    viz = ResultVisualizer()
    progress = current / total if total > 0 else 0
    print(f"\r{viz.format_progress_bar(progress, prefix=prefix)}", end="", flush=True)
    if current >= total:
        print()  # New line when complete


def format_duration(ms: int) -> str:
    """Format milliseconds as human-readable duration.
    
    Args:
        ms: Duration in milliseconds
        
    Returns:
        Human-readable duration string
    """
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms/1000:.2f}s"
    elif ms < 3600000:
        minutes = ms // 60000
        seconds = (ms % 60000) / 1000
        return f"{minutes}m {seconds:.1f}s"
    else:
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        return f"{hours}h {minutes}m"
