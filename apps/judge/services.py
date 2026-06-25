import io
import json
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


PYTHON_FUNCTION_COMMAND = ["python", "-I", "-B", "/sandbox/runner.py"]

PYTHON_FUNCTION_RUNNER = """\
import contextlib
import io
import json
from pathlib import Path


source = Path("/sandbox/solution.py").read_text(encoding="utf-8")
function_name = Path("/sandbox/function_name.txt").read_text(encoding="utf-8").strip()
payload = json.loads(Path("/sandbox/input.txt").read_text(encoding="utf-8"))
namespace = {"__name__": "submission"}
captured_stdout = io.StringIO()

with contextlib.redirect_stdout(captured_stdout):
    exec(compile(source, "/sandbox/solution.py", "exec"), namespace)

target = namespace.get(function_name)
if not callable(target):
    solution_class = namespace.get("Solution")
    if solution_class is not None:
        target = getattr(solution_class(), function_name, None)

if not callable(target):
    raise AttributeError(f"Callable '{function_name}' was not found in submission")

if isinstance(payload, dict) and ("args" in payload or "kwargs" in payload):
    args = payload.get("args", [])
    kwargs = payload.get("kwargs", {})
else:
    args = [payload]
    kwargs = {}

if not isinstance(args, list):
    raise TypeError("Test case 'args' must be a JSON array")
if not isinstance(kwargs, dict):
    raise TypeError("Test case 'kwargs' must be a JSON object")

with contextlib.redirect_stdout(captured_stdout):
    result = target(*args, **kwargs)

print(json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
"""


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
        configuration_error = _validate_function_test_case(test_case, index)
        if configuration_error:
            return JudgeResult(
                status=SubmissionStatus.INTERNAL_ERROR,
                message=configuration_error,
            )

        result = runner.run(
            code=submission.code,
            input_data=test_case.input_data,
            time_limit_ms=submission.problem.time_limit_ms,
            memory_limit_mb=submission.problem.memory_limit_mb,
            function_name=submission.problem.function_name,
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

        if not _outputs_equal(result.stdout, test_case.expected_output):
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
        function_name: str = "solve",
    ) -> TestCaseRunResult:
        client = _get_docker_client()
        self._ensure_image(client)

        container = None
        started_at = 0.0
        timeout_seconds = _timeout_seconds(time_limit_ms)

        try:
            container = client.containers.create(
                image=self.image,
                command=PYTHON_FUNCTION_COMMAND,
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
            container.put_archive(
                "/",
                _build_submission_archive(
                    code,
                    input_data,
                    function_name=function_name,
                ),
            )
            started_at = time.monotonic()
            container.start()
            wait_result = container.wait(timeout=timeout_seconds)
            runtime_ms = _elapsed_ms(started_at)
            container.reload()

            stdout_bytes, stdout_limit_exceeded = _read_limited_logs(
                container,
                stdout=True,
                stderr=False,
                limit=self.output_limit_bytes,
            )
            stderr_bytes, stderr_limit_exceeded = _read_limited_logs(
                container,
                stdout=False,
                stderr=True,
                limit=self.output_limit_bytes,
            )
            output_limit_exceeded = stdout_limit_exceeded or stderr_limit_exceeded

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


def _build_submission_archive(
    code: str,
    input_data: str,
    *,
    function_name: str = "solve",
) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        _add_directory(archive, "sandbox")
        _add_text_file(archive, "sandbox/solution.py", code, mode=0o444)
        _add_text_file(archive, "sandbox/input.txt", input_data, mode=0o444)
        _add_text_file(
            archive,
            "sandbox/function_name.txt",
            function_name,
            mode=0o444,
        )
        _add_text_file(
            archive,
            "sandbox/runner.py",
            PYTHON_FUNCTION_RUNNER,
            mode=0o444,
        )
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


def _read_limited_logs(
    container,
    *,
    stdout: bool,
    stderr: bool,
    limit: int,
) -> tuple[bytes, bool]:
    chunks = []
    captured = 0
    exceeded = False
    stream = container.logs(stdout=stdout, stderr=stderr, stream=True)

    try:
        for chunk in stream:
            if not chunk:
                continue

            available = max(0, limit - captured)
            if available:
                chunks.append(chunk[:available])
                captured += min(len(chunk), available)

            if len(chunk) > available:
                exceeded = True
                break
    finally:
        close = getattr(stream, "close", None)
        if close:
            close()

    return b"".join(chunks), exceeded


def _normalize_output(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.strip().splitlines())


def _validate_function_test_case(test_case, index: int) -> str | None:
    try:
        payload = json.loads(test_case.input_data)
    except json.JSONDecodeError as exc:
        return f"Test case #{index} has invalid input JSON: {exc.msg}."

    if isinstance(payload, dict) and ("args" in payload or "kwargs" in payload):
        if not isinstance(payload.get("args", []), list):
            return f"Test case #{index} field 'args' must be a JSON array."
        if not isinstance(payload.get("kwargs", {}), dict):
            return f"Test case #{index} field 'kwargs' must be a JSON object."

    try:
        json.loads(test_case.expected_output)
    except json.JSONDecodeError as exc:
        return f"Test case #{index} has invalid expected output JSON: {exc.msg}."

    return None


def _outputs_equal(actual: str, expected: str) -> bool:
    try:
        return json.loads(actual) == json.loads(expected)
    except json.JSONDecodeError:
        return False


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
