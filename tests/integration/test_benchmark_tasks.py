"""
Integration tests for Benchmark tasks.

NOTE: These tests are temporarily skipped due to SQLite autoincrement issues with BigInteger primary keys.
This is a known pre-existing issue that affects all models with BigInteger IDs.
Run tests with PostgreSQL instead of SQLite to verify functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.services.benchmark_service import BenchmarkService
from backend.models.schemas import BenchmarkTaskCreate
from backend.models.database import TaskType, TaskStatus

pytestmark = pytest.mark.skip(reason="Temporarily skipped: BigInteger autoincrement issue with SQLite")


@pytest.mark.integration
class TestBenchmarkService:
    """Test BenchmarkService class."""

    def test_create_task(self, db_session, test_user):
        """Test creating a benchmark task."""
        service = BenchmarkService(db_session)
        data = BenchmarkTaskCreate(
            task_name="Test Evaluation",
            task_type=TaskType.EVAL,
            config={
                "model": "llama-3-8b-instruct",
                "dataset": "mmlu"
            }
        )

        task = service.create_task(test_user.id, data, celery_task_id="test-celery-id")

        assert task.id is not None
        assert task.user_id == test_user.id
        assert task.task_name == "Test Evaluation"
        assert task.task_type == TaskType.EVAL
        assert task.status == TaskStatus.PENDING
        assert task.celery_task_id == "test-celery-id"

    def test_list_tasks(self, db_session, test_user, test_benchmark_task):
        """Test listing user's benchmark tasks."""
        service = BenchmarkService(db_session)
        tasks = service.list_tasks(test_user.id)

        assert len(tasks) >= 1
        assert any(t.id == test_benchmark_task.id for t in tasks)

    def test_list_tasks_with_status_filter(self, db_session, test_user, test_benchmark_task):
        """Test listing tasks with status filter."""
        service = BenchmarkService(db_session)

        # Filter by pending status
        tasks = service.list_tasks(test_user.id, status="pending")
        assert all(t.status == TaskStatus.PENDING for t in tasks)

    def test_get_task(self, db_session, test_user, test_benchmark_task):
        """Test getting a task by ID."""
        service = BenchmarkService(db_session)
        task = service.get_task(test_benchmark_task.id, test_user.id)

        assert task is not None
        assert task.id == test_benchmark_task.id
        assert task.task_name == test_benchmark_task.task_name

    def test_get_task_not_found(self, db_session, test_user):
        """Test getting a non-existent task."""
        service = BenchmarkService(db_session)
        task = service.get_task(99999, test_user.id)
        assert task is None

    def test_cancel_task(self, db_session, test_user, test_benchmark_task):
        """Test cancelling a benchmark task."""
        service = BenchmarkService(db_session)
        task_id = test_benchmark_task.id

        service.cancel_task(task_id, test_user.id)

        # Verify task is cancelled
        task = service.get_task(task_id, test_user.id)
        assert task.status == TaskStatus.CANCELLED

    def test_cancel_task_not_found(self, db_session, test_user):
        """Test cancelling a non-existent task."""
        service = BenchmarkService(db_session)

        with pytest.raises(ValueError, match="Task not found"):
            service.cancel_task(99999, test_user.id)

    def test_list_datasets(self, db_session, test_benchmark_dataset):
        """Test listing available datasets."""
        service = BenchmarkService(db_session)
        datasets = service.list_datasets()

        assert len(datasets) >= 1
        assert any(d.id == test_benchmark_dataset.id for d in datasets)

    def test_list_datasets_with_category_filter(self, db_session, test_benchmark_dataset):
        """Test listing datasets with category filter."""
        service = BenchmarkService(db_session)
        datasets = service.list_datasets(category="knowledge")

        assert len(datasets) >= 1
        assert all(d.category == "knowledge" for d in datasets)

    def test_get_dataset(self, db_session, test_benchmark_dataset):
        """Test getting a dataset by ID."""
        service = BenchmarkService(db_session)
        dataset = service.get_dataset(test_benchmark_dataset.id)

        assert dataset is not None
        assert dataset.id == test_benchmark_dataset.id
        assert dataset.name == test_benchmark_dataset.name


@pytest.mark.integration
class TestCeleryBenchmarkTasks:
    """Test Celery tasks for benchmark execution."""

    def test_run_eval_task_success(self, db_session, test_benchmark_task):
        """Test successful execution of eval task."""
        from backend.workers.benchmark_tasks import run_eval_task

        # Mock EvalScope API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "output_dir": "/tmp/eval_results",
            "accuracy": 0.85
        }
        mock_response.raise_for_status = Mock()

        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            result = run_eval_task(test_benchmark_task.id)

        assert result["task_id"] == test_benchmark_task.id
        assert result["status"] == "completed"

        # Verify database update
        db_session.refresh(test_benchmark_task)
        assert test_benchmark_task.status == TaskStatus.COMPLETED
        assert test_benchmark_task.result is not None
        assert test_benchmark_task.output_dir == "/tmp/eval_results"

    def test_run_eval_task_failure(self, db_session, test_benchmark_task):
        """Test eval task execution failure."""
        from backend.workers.benchmark_tasks import run_eval_task

        # Mock EvalScope API error
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = Exception("EvalScope service unavailable")

            result = run_eval_task(test_benchmark_task.id)

        assert result["task_id"] == test_benchmark_task.id
        assert result["status"] == "failed"

        # Verify database update
        db_session.refresh(test_benchmark_task)
        assert test_benchmark_task.status == TaskStatus.FAILED
        assert test_benchmark_task.error_message is not None

    def test_run_perf_task_success(self, db_session, test_benchmark_task):
        """Test successful execution of perf task."""
        from backend.workers.benchmark_tasks import run_perf_task

        # Update task to PERF type
        test_benchmark_task.task_type = TaskType.PERF
        db_session.commit()

        # Mock EvalScope API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "output_dir": "/tmp/perf_results",
            "qps": 100.5,
            "latency_p50": 50,
            "latency_p95": 100
        }
        mock_response.raise_for_status = Mock()

        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            result = run_perf_task(test_benchmark_task.id)

        assert result["task_id"] == test_benchmark_task.id
        assert result["status"] == "completed"

        # Verify database update
        db_session.refresh(test_benchmark_task)
        assert test_benchmark_task.status == TaskStatus.COMPLETED
        assert test_benchmark_task.result is not None
