import io
import tarfile
import time
from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class JudgeResult:
    status: str
    message: str
    runtime_ms: int | None = None
    memory_kb: int | None = None


@dataclass(frozen=True)
class TestCaseRunResult:
    status: str
    stdout: str = ""
    stderr: str = ""
    runtime_ms: int = 0
    memory_kb: int | None = None
    exit_code: int | None = None
    timed_out: bool = False
    oom_killed: bool = False
    output_limit_exceeded: bool = False


class JudgeRuntimeError(RuntimeError):
    pass


PYTHON_RUN_COMMAND = [
    "python",
    "-I",
    "-B",
    "-c",
    (
        "import runpy, sys; "
        "sys.stdin = open('/sandbox/input.txt', 'r', encoding='utf-8'); "
        "runpy.run_path('/sandbox/solution.py', run_name='__main__')"
    ),
]


def evaluate_submission(submission) -> JudgeResult:
    from apps.submissions.models import Language, SubmissionStatus

    if submission.language != Language.PYTHON:
        return JudgeResult(
            status=SubmissionStatus.INTERNAL_ERROR,
            message="Only Python submissions are supported by the current judge runner.",
        )

    test_cases = list(submission.problem.test_cases.all())
    if not test_cases:
        return JudgeResult(
            status=SubmissionStatus.INTERNAL_ERROR,
            message="Problem has no test cases configured.",
        )

    runner = DockerPythonRunner()
    total_runtime_ms = 0
    peak_memory_kb = 0

    for index, test_case in enumerate(test_cases, start=1):
        result = runner.run(
            code=submission.code,
            input_data=test_case.input_data,
            time_limit_ms=submission.problem.time_limit_ms,
            memory_limit_mb=submission.problem.memory_limit_mb,
        )
        total_runtime_ms += result.runtime_ms
        peak_memory_kb = max(peak_memory_kb, result.memory_kb or 0)

        if result.timed_out:
            return JudgeResult(
                status=SubmissionStatus.TIME_LIMIT,
                message=f"Time limit exceeded on test case #{index}.",
                runtime_ms=total_runtime_ms,
                memory_kb=peak_memory_kb or None,
            )

        if result.oom_killed:
            return JudgeResult(
                status=SubmissionStatus.MEMORY_LIMIT,
                message=f"Memory limit exceeded on test case #{index}.",
                runtime_ms=total_runtime_ms,
                memory_kb=peak_memory_kb or None,
            )

        if result.output_limit_exceeded:
            return JudgeResult(
                status=SubmissionStatus.RUNTIME_ERROR,
                message=f"Output limit exceeded on test case #{index}.",
                runtime_ms=total_runtime_ms,
                memory_kb=peak_memory_kb or None,
            )

        if result.exit_code != 0:
            status = _classify_python_error(result.stderr, SubmissionStatus)
            return JudgeResult(
                status=status,
                message=_format_execution_error(index, result.stderr, result.exit_code),
                runtime_ms=total_runtime_ms,
                memory_kb=peak_memory_kb or None,
            )

        if _normalize_output(result.stdout) != _normalize_output(test_case.expected_output):
            return JudgeResult(
                status=SubmissionStatus.WRONG_ANSWER,
                message=_format_wrong_answer(index, test_case.expected_output, result.stdout),
                runtime_ms=total_runtime_ms,
                memory_kb=peak_memory_kb or None,
            )

    return JudgeResult(
        status=SubmissionStatus.ACCEPTED,
        message=f"Accepted {len(test_cases)}/{len(test_cases)} test cases.",
        runtime_ms=total_runtime_ms,
        memory_kb=peak_memory_kb or None,
    )


class DockerPythonRunner:
    def __init__(self):
        self.image = settings.JUDGE_PYTHON_IMAGE
        self.output_limit_bytes = settings.JUDGE_OUTPUT_LIMIT_BYTES

    def run(
        self,
        *,
        code: str,
        input_data: str,
        time_limit_ms: int,
        memory_limit_mb: int,
    ) -> TestCaseRunResult:
        client = _get_docker_client()
        self._ensure_image(client)

        container = None
        started_at = 0.0
        timeout_seconds = _timeout_seconds(time_limit_ms)

        try:
            container = client.containers.create(
                image=self.image,
                command=PYTHON_RUN_COMMAND,
                detach=True,
                environment={
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONIOENCODING": "utf-8",
                    "PYTHONUNBUFFERED": "1",
                },
                labels={"app": "meadowcode", "component": "judge"},
                network_disabled=True,
                security_opt=["no-new-privileges"],
                tmpfs={"/tmp": "rw,noexec,nosuid,size=64m"},
                user=settings.JUDGE_DOCKER_USER,
                working_dir="/sandbox",
                **_resource_limits(memory_limit_mb),
            )
            container.put_archive("/", _build_submission_archive(code, input_data))
            started_at = time.monotonic()
            container.start()
            wait_result = container.wait(timeout=timeout_seconds)
            runtime_ms = _elapsed_ms(started_at)
            container.reload()

            stdout_bytes = container.logs(stdout=True, stderr=False)
            stderr_bytes = container.logs(stdout=False, stderr=True)
            output_limit_exceeded = (
                len(stdout_bytes) > self.output_limit_bytes
                or len(stderr_bytes) > self.output_limit_bytes
            )

            state = container.attrs.get("State", {})
            return TestCaseRunResult(
                status="finished",
                stdout=_decode_limited(stdout_bytes, self.output_limit_bytes),
                stderr=_decode_limited(stderr_bytes, self.output_limit_bytes),
                runtime_ms=runtime_ms,
                memory_kb=_read_memory_kb(container),
                exit_code=wait_result.get("StatusCode"),
                timed_out=runtime_ms > time_limit_ms,
                oom_killed=bool(state.get("OOMKilled")),
                output_limit_exceeded=output_limit_exceeded,
            )
        except Exception as exc:
            if _is_docker_wait_timeout(exc):
                runtime_ms = _elapsed_ms(started_at)
                if container is not None:
                    _kill_container(container)
                return TestCaseRunResult(
                    status="timeout",
                    runtime_ms=runtime_ms,
                    timed_out=True,
                )
            raise JudgeRuntimeError(f"Docker judge runner failed: {exc}") from exc
        finally:
            if container is not None:
                _remove_container(container)

    def _ensure_image(self, client) -> None:
        if not settings.JUDGE_PULL_IMAGE:
            return
        client.images.pull(self.image)


def _get_docker_client():
    try:
        import docker
        from docker.errors import DockerException
    except ImportError as exc:
        raise JudgeRuntimeError(
            "Docker SDK is not installed. Add the 'docker' package to the worker environment."
        ) from exc

    try:
        return docker.from_env()
    except DockerException as exc:
        raise JudgeRuntimeError(
            "Docker daemon is unavailable. Check Docker socket access for the Celery worker."
        ) from exc


def _is_docker_wait_timeout(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    if exc.__class__.__name__ in {"ReadTimeout", "ReadTimeoutError"}:
        return True
    return "read timed out" in str(exc).lower()


def _resource_limits(memory_limit_mb: int) -> dict:
    limits = {
        "cap_drop": ["ALL"],
        "mem_limit": f"{memory_limit_mb}m",
        "memswap_limit": f"{memory_limit_mb}m",
        "pids_limit": settings.JUDGE_DOCKER_PIDS_LIMIT,
    }
    if settings.JUDGE_DOCKER_NANO_CPUS:
        limits["nano_cpus"] = settings.JUDGE_DOCKER_NANO_CPUS
    return limits


def _build_submission_archive(code: str, input_data: str) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        _add_directory(archive, "sandbox")
        _add_text_file(archive, "sandbox/solution.py", code, mode=0o444)
        _add_text_file(archive, "sandbox/input.txt", input_data, mode=0o444)
    buffer.seek(0)
    return buffer.getvalue()


def _add_directory(archive: tarfile.TarFile, name: str) -> None:
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.mode = 0o755
    archive.addfile(info)


def _add_text_file(
    archive: tarfile.TarFile,
    name: str,
    content: str,
    *,
    mode: int,
) -> None:
    payload = content.encode("utf-8")
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mode = mode
    archive.addfile(info, io.BytesIO(payload))


def _timeout_seconds(time_limit_ms: int) -> float:
    base_timeout = time_limit_ms / 1000
    return max(
        settings.JUDGE_MIN_TIMEOUT_SECONDS,
        base_timeout + settings.JUDGE_TIMEOUT_GRACE_SECONDS,
    )


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))


def _read_memory_kb(container) -> int | None:
    try:
        stats = container.stats(stream=False)
    except Exception:
        return None

    usage_bytes = stats.get("memory_stats", {}).get("usage")
    if usage_bytes is None:
        return None
    return int(usage_bytes / 1024)


def _kill_container(container) -> None:
    try:
        container.kill()
    except Exception:
        pass


def _remove_container(container) -> None:
    try:
        container.remove(force=True)
    except Exception:
        pass


def _decode_limited(payload: bytes, limit: int) -> str:
    return payload[:limit].decode("utf-8", errors="replace")


def _normalize_output(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.strip().splitlines())


def _classify_python_error(stderr: str, statuses):
    if "SyntaxError" in stderr or "IndentationError" in stderr:
        return statuses.COMPILE_ERROR
    return statuses.RUNTIME_ERROR


def _format_execution_error(index: int, stderr: str, exit_code: int | None) -> str:
    details = stderr.strip() or "Process exited without stderr."
    return f"Runtime failed on test case #{index} with exit code {exit_code}: {details}"


def _format_wrong_answer(index: int, expected: str, actual: str) -> str:
    return (
        f"Wrong answer on test case #{index}. "
        f"Expected: {_shorten(expected)}. Got: {_shorten(actual)}."
    )


def _shorten(value: str, limit: int = 500) -> str:
    normalized = _normalize_output(value)
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."
