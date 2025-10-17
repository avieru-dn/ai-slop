# Python Code Standards

## General Principles

- Follow PEP 8 style guide
- Use type hints for all functions and classes
- Write self-documenting code with clear names
- Keep functions small and focused (single responsibility)
- Prefer composition over inheritance
- Use context managers for resource management

## Code Structure

### Type Hints
```python
from typing import List, Dict, Optional, Union, Tuple, Any
from pathlib import Path

def process_data(
    input_data: List[Dict[str, Any]],
    threshold: float = 0.5,
    output_path: Optional[Path] = None
) -> Tuple[int, List[str]]:
    """
    Process input data and return results.
    
    Args:
        input_data: List of dictionaries containing data to process
        threshold: Minimum value threshold (default: 0.5)
        output_path: Optional path to write output file
    
    Returns:
        Tuple of (count of processed items, list of warnings)
    
    Raises:
        ValueError: If input_data is empty
        IOError: If output_path is not writable
    """
    if not input_data:
        raise ValueError("input_data cannot be empty")
    
    # Implementation here
    count = len(input_data)
    warnings: List[str] = []
    
    return count, warnings
```

### Class Structure
```python
from dataclasses import dataclass
from typing import ClassVar

@dataclass
class MetricsCollector:
    """
    Collector for application metrics.
    
    Attributes:
        name: Name of the collector
        interval: Collection interval in seconds
        enabled: Whether collection is enabled
    """
    name: str
    interval: int = 60
    enabled: bool = True
    
    # Class variable
    MAX_RETRIES: ClassVar[int] = 3
    
    def __post_init__(self) -> None:
        """Validate attributes after initialization."""
        if self.interval < 0:
            raise ValueError("interval must be non-negative")
    
    def collect(self) -> Dict[str, float]:
        """
        Collect metrics.
        
        Returns:
            Dictionary of metric names to values
        """
        if not self.enabled:
            return {}
        
        # Implementation
        return {"metric1": 1.0}
```

## Error Handling

### Exception Handling
```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def safe_division(a: float, b: float) -> Optional[float]:
    """
    Safely divide two numbers.
    
    Args:
        a: Numerator
        b: Denominator
    
    Returns:
        Result of division or None if division by zero
    """
    try:
        result = a / b
        return result
    except ZeroDivisionError:
        logger.warning(f"Division by zero attempted: {a} / {b}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in division: {e}", exc_info=True)
        raise

def process_file(file_path: Path) -> str:
    """
    Process a file and return its contents.
    
    Args:
        file_path: Path to file to process
    
    Returns:
        File contents as string
    
    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file is not readable
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    try:
        return file_path.read_text(encoding="utf-8")
    except PermissionError:
        logger.error(f"Permission denied reading file: {file_path}")
        raise
```

## Context Managers

### Resource Management
```python
from contextlib import contextmanager
from typing import Iterator, Any

@contextmanager
def database_connection(connection_string: str) -> Iterator[Any]:
    """
    Context manager for database connections.
    
    Args:
        connection_string: Database connection string
    
    Yields:
        Database connection object
    """
    conn = None
    try:
        conn = create_connection(connection_string)
        logger.info("Database connection established")
        yield conn
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")

# Usage
with database_connection("postgres://...") as conn:
    # Use connection
    pass
```

## Logging

### Proper Logging Setup
```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Configure application logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    handlers: List[logging.Handler] = [
        logging.StreamHandler()
    ]
    
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )

# Usage in code
logger = logging.getLogger(__name__)

# Don't use print(), use logging
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)  # Include traceback
logger.critical("Critical error")
```

## Testing

### Unit Tests with pytest
```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

class TestMetricsCollector:
    """Tests for MetricsCollector class."""
    
    @pytest.fixture
    def collector(self) -> MetricsCollector:
        """Fixture providing a MetricsCollector instance."""
        return MetricsCollector(name="test", interval=30)
    
    def test_initialization(self, collector: MetricsCollector) -> None:
        """Test collector initialization."""
        assert collector.name == "test"
        assert collector.interval == 30
        assert collector.enabled is True
    
    def test_invalid_interval(self) -> None:
        """Test that negative interval raises ValueError."""
        with pytest.raises(ValueError, match="interval must be non-negative"):
            MetricsCollector(name="test", interval=-1)
    
    @patch("module.external_api_call")
    def test_collect_with_mock(
        self,
        mock_api: Mock,
        collector: MetricsCollector
    ) -> None:
        """Test collect method with mocked external API."""
        mock_api.return_value = {"metric1": 1.0}
        
        result = collector.collect()
        
        assert result == {"metric1": 1.0}
        mock_api.assert_called_once()
    
    @pytest.mark.parametrize("interval,expected", [
        (10, True),
        (60, True),
        (120, True),
    ])
    def test_intervals(self, interval: int, expected: bool) -> None:
        """Test various interval values."""
        collector = MetricsCollector(name="test", interval=interval)
        assert (collector.interval > 0) == expected
```

## Environment Variables

### Configuration Management
```python
import os
from typing import Optional
from dataclasses import dataclass

@dataclass
class Config:
    """Application configuration."""
    
    # Required settings
    api_key: str
    database_url: str
    
    # Optional settings with defaults
    log_level: str = "INFO"
    timeout: int = 30
    max_retries: int = 3
    
    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables.
        
        Returns:
            Config instance
        
        Raises:
            ValueError: If required environment variables are missing
        """
        api_key = os.getenv("API_KEY")
        if not api_key:
            raise ValueError("API_KEY environment variable is required")
        
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        return cls(
            api_key=api_key,
            database_url=database_url,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            timeout=int(os.getenv("TIMEOUT", "30")),
            max_retries=int(os.getenv("MAX_RETRIES", "3"))
        )

# Usage
config = Config.from_env()
```

## Async/Await

### Asynchronous Code
```python
import asyncio
from typing import List
import aiohttp

async def fetch_url(
    session: aiohttp.ClientSession,
    url: str
) -> str:
    """
    Fetch URL content asynchronously.
    
    Args:
        session: aiohttp client session
        url: URL to fetch
    
    Returns:
        Response text
    """
    async with session.get(url) as response:
        return await response.text()

async def fetch_multiple_urls(urls: List[str]) -> List[str]:
    """
    Fetch multiple URLs concurrently.
    
    Args:
        urls: List of URLs to fetch
    
    Returns:
        List of response texts
    """
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        return await asyncio.gather(*tasks)

# Usage
urls = ["http://example.com", "http://example.org"]
results = asyncio.run(fetch_multiple_urls(urls))
```

## File Operations

### Path Operations
```python
from pathlib import Path
from typing import List
import json

def read_json_file(file_path: Path) -> Dict[str, Any]:
    """
    Read and parse JSON file.
    
    Args:
        file_path: Path to JSON file
    
    Returns:
        Parsed JSON data
    
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def write_json_file(file_path: Path, data: Dict[str, Any]) -> None:
    """
    Write data to JSON file.
    
    Args:
        file_path: Path to output JSON file
        data: Data to write
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Written data to {file_path}")
```

## Dependencies

### requirements.txt Format
```
# Core dependencies
requests>=2.31.0,<3.0.0
python-dotenv>=1.0.0,<2.0.0

# Azure SDK
azure-identity>=1.15.0,<2.0.0
azure-storage-blob>=12.19.0,<13.0.0

# Monitoring
prometheus-client>=0.19.0,<1.0.0

# Development dependencies
pytest>=7.4.0,<8.0.0
pytest-cov>=4.1.0,<5.0.0
black>=23.7.0,<24.0.0
mypy>=1.5.0,<2.0.0
pylint>=2.17.0,<3.0.0
```

### pyproject.toml Format
```toml
[project]
name = "my-project"
version = "1.0.0"
description = "Project description"
requires-python = ">=3.11"

dependencies = [
    "requests>=2.31.0,<3.0.0",
    "python-dotenv>=1.0.0,<2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0,<8.0.0",
    "black>=23.7.0,<24.0.0",
    "mypy>=1.5.0,<2.0.0",
]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
```

## Best Practices Checklist

- ✅ All functions have type hints
- ✅ All functions have docstrings
- ✅ Use logging instead of print()
- ✅ Proper exception handling
- ✅ Context managers for resources
- ✅ Environment variables for configuration
- ✅ Unit tests with good coverage
- ✅ No hardcoded values
- ✅ PEP 8 compliant
- ✅ Code is modular and reusable

